import logging
import tweepy

from traceback import print_exc
from tweepy.error import TweepError

from pytwitterbot import data_files
from pytwitterbot.file_helper import load_file_lines, load_commentable_file, store_file_lines

log = logging.getLogger(__name__)

TWEETS_COUNT_PER_SEARCH = 30


class RetweetBot(object):
    def __init__(self, client):
        super(RetweetBot, self).__init__()
        self.client = client
        self.queries = load_commentable_file(data_files.SEARCH_FOR)
        self.marked_as_retweeted = set(load_file_lines(data_files.MARKED_AS_RETWEETED))
        self.muted_text = set(load_commentable_file(data_files.MUTED_TEXT))
        self.muted_user_ids = set(load_commentable_file(data_files.MUTED_USER_IDS))
        self.muted_usernames = set(load_commentable_file(data_files.MUTED_USERNAMES))
        self.bot_user_id = client.me().id_str

    def start(self):
        for query in self.queries:
            log.info(f'Searching for: {query}')
            cursor = tweepy.Cursor(
                self.client.search,
                q=f'{query} -filter:retweets',
                count=TWEETS_COUNT_PER_SEARCH,
                result_type='recent',
                include_entities=False,
            )

            recent_tweets = []
            for tweet in cursor.items():
                if len(recent_tweets) >= TWEETS_COUNT_PER_SEARCH:
                    break
                recent_tweets.append(tweet)

            for tweet in reversed(recent_tweets):
                if self.should_retweet(tweet):
                    self.retweet(tweet)

            store_file_lines(
                data_files.MARKED_AS_RETWEETED,
                list(sorted(self.marked_as_retweeted)),
            )

    def retweet(self, tweet):
        try:
            log.info(f'Will retweet. tweet id: {tweet.id_str}, created at: {tweet.created_at}, text:\n' + tweet.text)
            tweet.retweet()
            log.info('Retweeted successfully')
            self.marked_as_retweeted.append(tweet.id_str)
        except TweepError as e:
            if e.api_code == 327:
                self.marked_as_retweeted.append(tweet.id_str)
            else:
                log.error(e)
                log.exception(e)
        except Exception as e:
            print_exc()
            log.error(e)
            log.exception(e)

    def should_retweet(self, tweet: tweepy.Status):
        text = tweet.text
        user_id = tweet.user.id_str
        username = tweet.user.screen_name

        if tweet.id_str in self.marked_as_retweeted:
            return False

        for pattern in self.muted_text:
            if len(pattern) > 0 and text.find(pattern) >= 0:
                log.info(f'Skip tweet for muled pattern: |{pattern}|, text:\n' + text)
                return False

        if self.bot_user_id == user_id:
            log.info('Skipped tweet from self.')
            return False

        if user_id in self.muted_user_ids:
            log.info(f'Skipped tweet from muted user id: {user_id}, text:\n' + text)
            return False

        if username in self.muted_usernames:
            log.info(f'Skipped tweet from muted username: {username}, text:\n' + text)
            return False

        return True
