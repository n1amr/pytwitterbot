from traceback import print_exc

import tweepy
from tweepy.error import TweepError

from pytwitterbot import data_files
from pytwitterbot.file_helper import load_file_lines, load_queries_file, store_file_lines

TWEETS_COUNT_PER_SEARCH = 30


class RetweetBot(object):
    def __init__(self, client):
        super(RetweetBot, self).__init__()
        self.client = client
        self.queries = load_queries_file(data_files.SEARCH_FOR)
        self.marked_as_retweeted = load_file_lines(
            data_files.MARKED_AS_RETWEETED)
        self.muted_text = load_file_lines(data_files.MUTED_TEXT)
        self.muted_user_ids = load_file_lines(data_files.MUTED_USER_IDS)
        self.bot_user_id = client.me().id_str

    def start(self):
        for query in self.queries:
            print('searching for', query)
            cursor = tweepy.Cursor(self.client.search,
                                   q='{} -filter:retweets'.format(query),
                                   count=TWEETS_COUNT_PER_SEARCH,
                                   result_type='recent', include_entities=False)
            cursor_items = cursor.items()
            recent_tweets = []
            for tweet in cursor_items:
                if len(recent_tweets) >= TWEETS_COUNT_PER_SEARCH:
                    break
                recent_tweets.append(tweet)

            for tweet in reversed(recent_tweets):
                if tweet.id_str in self.marked_as_retweeted:
                    continue

                user_id = tweet.user.id_str
                if (self.bot_user_id == user_id or
                            user_id in self.muted_user_ids):
                    continue

                skip = False
                for pattern in self.muted_text:
                    if len(pattern) > 0 and tweet.text.find(pattern) >= 0:
                        skip = True
                        break

                if not skip:
                    try:
                        self.retweet(tweet)
                        self.marked_as_retweeted.append(tweet.id_str)
                    except TweepError as e:
                        print(e)
                        if e.api_code == 327:
                            self.marked_as_retweeted.append(tweet.id_str)
                    except Exception:
                        print_exc()

            self.marked_as_retweeted.sort()
            store_file_lines(data_files.MARKED_AS_RETWEETED,
                             self.marked_as_retweeted)

    def retweet(self, tweet):
        print('=' * 50)
        print('retweeting #{}, created at: {}'.format(tweet.id_str, tweet.created_at))
        print(tweet.text)
        tweet.retweet()
        print('=' * 50)
        print()
