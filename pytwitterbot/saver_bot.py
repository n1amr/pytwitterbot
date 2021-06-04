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


class SaverBot:
    def __init__(self, twitter, config: Config):
        super(SaverBot, self).__init__()

        self.config = config
        self.twitter = twitter
        self.bot_user = self.twitter.me()
        self.bot_user_id = self.bot_user.id_str

        self.marked_as_saved = self.config.marked_as_saved

        self.settings = self.config.settings['bots.saver.config']
        self.root_path = self.settings['root_path']
        self.list_name = self.settings['list_name']
        self.list = self.twitter.get_list(
            owner_screen_name=self.bot_user.screen_name,
            slug=self.list_name,
        )

        self.max_saved_tweets = self.settings.get('max_saved_tweets', MAX_SAVED_TWEETS)
        self.max_tweets_to_fetch = self.settings.get('max_tweets_to_fetch', MAX_TWEETS_TO_FETCH)

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

        try:
            _log_statistics(
                all_tweets,
                os.path.join(self.config.bot_home, 'stats.tsv')
            )
        except Exception as e:
            log.exception(e)
            log.error(e)

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


def _log_statistics(tweets: List[Status], save_path: str):
    import pandas as pd
    pd.set_option('display.max_columns', 100)
    pd.set_option('display.max_rows', 10000)
    pd.set_option('display.width', 1000)

    user_to_tweets = {}
    for tweet in tweets:
        if datetime.datetime.utcnow() - tweet.created_at > datetime.timedelta(days=1):
            continue
        user = tweet.user.screen_name
        user_to_tweets.setdefault(user, []).append(tweet)
    total_tweets_count = sum(len(tweets) for user, tweets in user_to_tweets.items())

    data = []
    for user, tweets in user_to_tweets.items():
        count = len(tweets)
        retweets_count = sum(1 for tweet in tweets if 'retweeted_status' in tweet._json)
        length_sum = sum(len(tweet.text) for tweet in tweets)
        length_average = length_sum / count
        last_tweet_time = max(tweet.created_at for tweet in tweets)
        data.append({
            'user': user,
            'total_tweets_length': length_sum,
            'tweets_count': count,
            'tweets_count_percentage': 100 * count / total_tweets_count,
            'retweets_count': retweets_count,
            'average_tweet_length': length_average,
            'last_tweeted_at': last_tweet_time,
        })

    df = pd.DataFrame.from_records(data)
    df = df.sort_values(
        by=[
            # 'tweets_count',
            # 'average_tweet_length',
            'total_tweets_length',
        ],
        ascending=False,
        ignore_index=True,
    )

    def print_df(df):
        log.info(f'\n{df}')

    print_df(df)
    if len(df) > 30:
        print_df(df.head(30))

    df.to_csv(save_path, sep='\t')

    log.info(f'Saved statistics at: {save_path}')
