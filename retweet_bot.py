from file_helper import load_file_lines, store_file_lines
import tweepy
from traceback import print_exc

# TWEETS_COUNT_PER_SEARCH = 30
TWEETS_COUNT_PER_SEARCH = 3


class RetweetBot(object):

    def __init__(self, client):
        super(RetweetBot, self).__init__()
        self.client = client
        self.queries = load_file_lines('search_for')
        self.marked_as_retweeted = load_file_lines('marked_as_retweeted')
        self.muted_text = load_file_lines('muted_text')
        self.muted_user_ids = load_file_lines('muted_user_ids')
        self.bot_user_id = client.me().id_str

    def start(self):
        for query in self.queries:
            print('Searching for', query)
            tweets = tweepy.Cursor(self.client.search,
                                   q=query + ' -filter:retweets',
                                   count=TWEETS_COUNT_PER_SEARCH,
                                   result_type='recent',
                                   include_entities=False).items()
            for i, tweet in enumerate(tweets):
                if i >= TWEETS_COUNT_PER_SEARCH:
                    break

                if tweet.id_str in self.marked_as_retweeted:
                    continue

                user_id = tweet.user.id_str
                if (self.bot_user_id == user_id or
                        user_id in self.muted_user_ids):
                    continue

                skip = False
                for pattern in self.muted_text:
                    if tweet.text.find(pattern) >= 0:
                        skip = True
                        break

                if not skip:
                    try:
                        self.retweet(tweet)
                    except Exception:
                        print_exc()

                self.marked_as_retweeted.append(tweet.id_str)
            self.marked_as_retweeted.sort()
            store_file_lines('marked_as_retweeted', self.marked_as_retweeted)

    def retweet(self, tweet):
        print('=' * 50)
        print('Retweeting #' + tweet.id_str)
        print(tweet.text)
        tweet.retweet()
        print('=' * 50)
        print()
