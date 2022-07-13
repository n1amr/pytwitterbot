import datetime
import json
import logging
import os
import re
import requests
import tweepy

from pytwitterbot.config import Config
from time import sleep
from tweepy.models import Status
from typing import List

from pytwitterbot.file_utils import (
    ensure_parent_dir,
    load_text,
    write_json,
    write_text,
)


log = logging.getLogger(__name__)

TWEETS_VAR_NAME = 'Grailbird.data.tweets = '
TWEETS_INDEX_VAR_NAME = 'var tweet_index = '

MAX_SAVED_TWEETS = 100_000
MAX_TWEETS_TO_FETCH = 100


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

        self.max_saved_tweets = self.settings.get('max_saved_tweets', MAX_SAVED_TWEETS)
        self.max_tweets_to_fetch = self.settings.get('max_tweets_to_fetch', MAX_TWEETS_TO_FETCH)

        breakpoint()

    def start(self):
        log.info(f'Fetching tweets')
        new_tweets = self.fetch_tweets()
        log.info(f'Fetched {len(new_tweets)} new tweets.')

        log.info('Downloading media')
        new_tweets = self.download_media_and_adjust_urls(new_tweets)

        saved_tweets = self.load_tweets()
        log.info(f'Loaded {len(saved_tweets)} saved tweets.')

        all_tweets = new_tweets + saved_tweets
        all_tweets = _deduplicate_tweets(all_tweets)
        all_tweets = _sort_tweets(all_tweets)
        all_tweets = all_tweets[:self.max_saved_tweets]
        self.store_tweets(all_tweets)
        log.info(f'Saved {len(all_tweets)} tweets.')

        for tweet in all_tweets:
            self.config.mark_saved(tweet.id)
        self.config.commit_saved_marks()

    def fetch_tweets(self) -> List[Status]:
        timeline = tweepy.Cursor(
            self.twitter.list_timeline,
            list_id=self.list.id,
            count=20,
            include_entities=True,
        ).items()

        max_count = min(self.max_saved_tweets, self.max_tweets_to_fetch)
        found_saved = None

        tweets = []
        while len(tweets) < max_count:
            tweet = None
            for trial in range(20):
                try:
                    tweet = timeline.next()
                    break
                except StopIteration as e:
                    break
                except Exception as e:
                    log.exception(e)
                    log.error(e)
                    log.error(f'Next trial: {trial + 2}')
                    sleep(5)

            if tweet is None:
                log.error(f'Failed to fetch next tweet.')
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
                log.debug(f'Found a saved tweet. id: {id}')
                found_saved = id
                # break # Uncomment after verifying
            else:
                log.debug(f'Keeping tweet. id: {id}')
                if found_saved is not None:
                    log.error(f'Found a new tweet {id} tweet after a saved tweet {found_saved}')

        return tweets

    @property
    def _tweets_path(self):
        return os.path.join(self.root_path, 'data', 'js', 'tweets', 'tweets.js')

    @property
    def _tweets_index_path(self):
        return os.path.join(self.root_path, 'data', 'js', 'tweet_index.js')

    def load_tweets(self) -> List[Status]:
        tweets = []

        if not os.path.exists(self._tweets_path):
            self.store_tweets(tweets)

        content = load_text(self._tweets_path)
        assert content.startswith(TWEETS_VAR_NAME), content[:100]
        json_content = content[len(TWEETS_VAR_NAME):]

        raw_tweets = json.loads(json_content)
        tweets = Status.parse_list(self.twitter, raw_tweets)
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
            tweet_json = tweet._json
            new_tweet_json = json.loads(json.dumps(tweet_json))
            self.search_for_media_urls(new_tweet_json)
            new_tweet = Status.parse(self.twitter, new_tweet_json)
            new_tweets.append(new_tweet)
        return new_tweets

    def search_for_media_urls(self, data):
        keys_to_extract = [
            'profile_image_url',
            'profile_image_url_https',
            'media_url',
            'media_url_https',
        ]

        if isinstance(data, list):
            for item in data:
                self.search_for_media_urls(item)

        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    if key in keys_to_extract or key == 'url' and value.find('pbs.twimg') >= 0:
                        data[key] = self.download_media_url(value)
                else:
                    self.search_for_media_urls(value)

    def download_media_url(self, media_url: str) -> str:
        relpath = re.sub(r'^https?://', '', media_url)
        output_path = os.path.join(self.root_path, relpath)

        if os.path.isfile(output_path):
            return media_url

        # http_media_url = f'http://{relpath}'
        log.info(f'Downloading {media_url} to {output_path}')

        trials = 20
        while True:
            try:
                trials -= 1
                response = requests.get(media_url)
                response.raise_for_status()
                data = response.content
                break
            except Exception as e:
                log.exception(e)
                log.error(e)
                log.warning(response.status_code)
                if trials == 0:
                    log.exception(e)
                    return media_url
                    pass
                    break
                    # raise

        ensure_parent_dir(output_path)
        with open(output_path, 'wb') as f:
            f.write(data)

        return media_url


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
