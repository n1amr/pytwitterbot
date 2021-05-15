import logging
import tweepy

from traceback import print_exc
from tweepy.error import TweepError

from pytwitterbot.config import Config

log = logging.getLogger(__name__)


class RetweetBot:
    def __init__(self, twitter: tweepy.API, config: Config):
        super(RetweetBot, self).__init__()

        self.twitter = twitter
        self.bot_user_id = twitter.me().id_str

        self.config = config

        self.marked_as_retweeted_path = config.marked_as_retweeted

        self.queries = config.queries
        self.marked_as_retweeted = config.marked_as_retweeted
        self.muted_text = config.muted_text
        self.muted_user_ids = config.muted_user_ids
        self.muted_usernames = config.muted_usernames


    def start(self):
        for query in self.queries:
            log.info(f'Searching for: {query}')
            cursor = tweepy.Cursor(
                self.twitter.search,
                q=f'{query} -filter:retweets',
                count=self.config.tweets_count_per_search,
                result_type='recent',
                include_entities=False,
            )

            recent_tweets = []
            for tweet in cursor.items():
                if len(recent_tweets) >= self.config.tweets_count_per_search:
                    break
                recent_tweets.append(tweet)

            for tweet in reversed(recent_tweets):
                if self.should_retweet(tweet):
                    self.retweet(tweet)

            self.config.commit_retweeted_marks()

    def retweet(self, tweet):
        try:
            log.info(f'Will retweet. tweet id: {tweet.id_str}, created at: {tweet.created_at}, text:\n' + tweet.text)
            tweet.retweet()
            log.info('Retweeted successfully')
            self.config.mark_retweeted(tweet.id_str)
        except TweepError as e:
            if e.api_code == 327:
                self.config.mark_retweeted(tweet.id_str)
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
                log.debug(f'Skip tweet for muled pattern: |{pattern}|, text:\n' + text)
                return False

        if self.bot_user_id == user_id:
            log.debug('Skipped tweet from self.')
            return False

        if user_id in self.muted_user_ids:
            log.debug(f'Skipped tweet from muted user id: {user_id}, text:\n' + text)
            return False

        if username in self.muted_usernames:
            log.debug(f'Skipped tweet from muted username: {username}, text:\n' + text)
            return False

        return True
