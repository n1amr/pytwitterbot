import json
import logging
import os
import re
import requests
import time
import tweepy

from tweepy.models import Status
from typing import Dict, Iterable, List, Tuple

from pytwitterbot.config import Config
from pytwitterbot.file_utils import (
    ensure_parent_dir,
    load_text,
    write_json,
    write_text,
)


log = logging.getLogger(__name__)

TWEETS_VAR_NAME = 'Grailbird.data.tweets = '
TWEETS_INDEX_VAR_NAME = 'var tweet_index = '

MAX_TWEETS_TO_FETCH = 100

RETRY_COUNT = 20
RETRY_DELAY_SECONDS = 5


class FavoriteSaverBot:
    def __init__(self, twitter: tweepy.API, auth_user: tweepy.User, config: Config):
        self.config = config
        self.twitter = twitter
        self.bot_user = auth_user
        self.bot_user_id = self.bot_user.id_str

        self.marked_as_saved = self.config.marked_as_saved

        self.settings = self.config.settings['bots.favorite_saver.config']
        self.root_path = self.settings['root_path']
        self.list_name = 'ALL'  # TODO
        self.list = self.twitter.get_list(
            owner_screen_name=self.bot_user.screen_name,
            slug=self.list_name,
        )

        self.max_tweets_to_fetch = self.settings.get('max_tweets_to_fetch', MAX_TWEETS_TO_FETCH)

    def start(self):
        log.info(f'Fetching tweets')
        new_tweets = self.fetch_tweets()
        log.info(f'Fetched {len(new_tweets)} new tweets.')

        log.info('Downloading media')
        new_tweets = self.download_media_and_adjust_urls(new_tweets)

        partitioned_new_tweets = self.partition_by_month(new_tweets)

        saved_tweets = self.load_partition(2022, 6)
        log.info(f'Loaded {len(saved_tweets)} saved tweets.')
        return

        all_tweets = new_tweets + saved_tweets
        all_tweets = _deduplicate_tweets(all_tweets)
        all_tweets = _sort_tweets(all_tweets)
        self.store_tweets(all_tweets)
        log.info(f'Saved {len(all_tweets)} tweets.')

        for tweet in all_tweets:
            self.config.mark_saved(tweet.id)

        self.config.commit_saved_marks()

    def fetch_tweets(self) -> List[Status]:
        tweet_count_per_fetch = 5
        use_cursor = False  # TODO
        if use_cursor:
            tweets_iterable = tweepy.Cursor(
                self.twitter.get_favorites,
                count=tweet_count_per_fetch,
                include_entities=True,
            ).items()
        else:
            tweets_iterable = self.twitter.get_favorites(count=tweet_count_per_fetch)
            tweets_iterable = iter(tweets_iterable)

        max_count = self.max_tweets_to_fetch
        found_saved = None

        tweets = []
        while len(tweets) < max_count:
            tweet = None
            for trial in range(RETRY_COUNT):
                try:
                    if use_cursor:
                        tweet = tweets_iterable.next()
                    else:
                        tweet = next(tweets_iterable)
                    break
                except StopIteration as e:
                    break
                except Exception as e:
                    log.exception(e)
                    log.error(e)
                    log.error(f'Next trial: {trial + 2}')

                    if trial < RETRY_COUNT - 1:
                        time.sleep(RETRY_DELAY_SECONDS)
                    else:
                        raise

            if tweet is None:
                log.error(f'Failed to fetch next tweet. Tweet is None.')
                break

            log.info(
                f'Fetched tweet.' +
                f' id: {tweet.id}' +
                f' created_at: {tweet.created_at}' +
                f' user: {tweet.user.screen_name}' +
                f' text: {tweet.text}'
            )
            tweets.append(tweet)

            id = tweet.id_str
            if id in self.marked_as_saved:
                log.debug(f'Found a saved tweet. Id: {id}.')
                found_saved = id
                break  # TODO: Uncomment after verifying.
            else:
                log.debug(f'Keeping tweet. Id: {id}.')
                if found_saved is not None:
                    log.error(f'Found a new tweet {id} tweet after a saved tweet {found_saved}.')

        return tweets

    @property
    def _tweets_path(self):
        return os.path.join(self.root_path, 'data', 'js', 'tweets', 'tweets.js')

    def get_tweets_partition_path(self, year: int, month: int):
        return os.path.join(self.root_path, 'data', 'js', 'tweets', f'{year:04}_{month:02}.js')

    @property
    def _tweets_index_path(self):
        return os.path.join(self.root_path, 'data', 'js', 'tweet_index.js')

    def load_partition(self, year: int, month: int) -> List[Status]:
        tweets = []

        partition_path = self.get_tweets_partition_path(year, month)

        if not os.path.exists(partition_path):
            log.warning(f'Could not load tweets from partition path: {partition_path}.')
            breakpoint()
            return tweets

        all_text_content = load_text(partition_path)
        assert all_text_content.startswith(TWEETS_VAR_NAME), all_text_content[:100]

        text_json_content = all_text_content[len(TWEETS_VAR_NAME):]

        data = json.loads(text_json_content)

        tweets = Status.parse_list(self.twitter, data)

        return tweets

    def store_tweets(self, tweets: List[Status]):
        json_tweets = [tweet._json for tweet in tweets]
        write_text(
            f'{TWEETS_VAR_NAME}{json.dumps(json_tweets)}',
            self._tweets_path,
        )
        write_json(json_tweets, f'{self._tweets_path}on')

        if os.path.isfile(self._tweets_index_path):
            tweet_index_content = load_text(self._tweets_index_path)
            assert tweet_index_content.startswith(TWEETS_INDEX_VAR_NAME), tweet_index_content[:100]
            tweet_index_json_content = tweet_index_content[len(TWEETS_INDEX_VAR_NAME):]
            tweet_index = json.loads(tweet_index_json_content)
        else:
            tweet_index = [{'tweet_count': 0}]

        tweet_index[0]['tweet_count'] = len(tweets)
        write_text(
            f'{TWEETS_INDEX_VAR_NAME}{json.dumps(tweet_index)}',
            self._tweets_index_path,
        )
        write_json(tweet_index, f'{self._tweets_index_path}on')

    def download_media_and_adjust_urls(self, tweets: List[Status]) -> List[Status]:
        new_tweets = []
        for tweet in tweets:
            tweet_json = json.loads(json.dumps(tweet._json))
            self.visit_media_urls(tweet_json)
            new_tweet = Status.parse(self.twitter, tweet_json)
            new_tweets.append(new_tweet)

        return new_tweets

    def visit_media_urls(self, json_data):
        keys_to_extract = [
            'profile_image_url',
            'profile_image_url_https',
            'media_url',
            'media_url_https',
        ]

        if isinstance(json_data, list):
            for item in json_data:
                self.visit_media_urls(item)

        elif isinstance(json_data, dict):
            for key, value in json_data.items():
                if isinstance(value, str):
                    should_download = (
                        key in keys_to_extract
                        or key == 'url' and 'pbs.twimg' in value
                    )
                    if should_download:
                        adjusted_url = self.download_media_url(value)
                        json_data[key] = adjusted_url
                else:
                    self.visit_media_urls(value)

    def download_media_url(self, media_url: str) -> str:
        relpath = re.sub(r'^https?://', '', media_url)
        output_path = os.path.join(self.root_path, 'media', relpath)  # TODO; Adjust path.

        if os.path.isfile(output_path):
            return media_url

        # http_media_url = f'http://{relpath}'
        log.info(f'Downloading {media_url} to {output_path}.')

        for trial in range(RETRY_COUNT):
            try:
                response = requests.get(media_url)

                response.raise_for_status()
                data = response.content

                _write(data, output_path)
                break
            except Exception as e:
                log.exception(e)
                log.error(e)
                log.warning(response.status_code)

                if trial >= RETRY_COUNT - 1:
                    log.exception(e)
                    return media_url

        # return media_url
        return relpath

    def partition_by_month(self, tweets: Iterable[Status]) -> Dict[Tuple[int, int], List[Status]]:
        partitioned_tweets = {}

        for tweet in tweets:
            dt = tweet.created_at
            key = (dt.year, dt.month)
            partitioned_tweets.setdefault(key, []).append(tweet)

        return partitioned_tweets


def _write(data: bytearray, path: str):
    ensure_parent_dir(path)
    with open(path, 'wb') as f:
        f.write(data)


def _sort_tweets(tweets):
    def _tweet_sort_key(tweet: Status):
        return (
            tweet.created_at,
            tweet.id,
        )

    return list(sorted(tweets, key=_tweet_sort_key, reverse=True))


def _deduplicate_tweets(tweets):
    stored_ids = set()
    result = []
    for tweet in tweets:
        id = tweet.id
        if id not in stored_ids:
            result.append(tweet)
            stored_ids.add(id)
    return result
