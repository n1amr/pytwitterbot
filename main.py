import file_helper
import data_files
from twitter_session import TwitterSession
from retweet_bot import RetweetBot
from tweet_bot import TweetBot
import sys


def main(args):
    root = None
    if len(args) > 1:
        root = args[1]

    data_files.init(root)
    file_helper.assert_all_files()
    session = TwitterSession()

    print('signed in as', session.twitter_client.me().name)

    bots = [TweetBot(session.twitter_client),
            RetweetBot(session.twitter_client)]

    for bot in bots:
        try:
            bot.start()
        except Exception as e:
            print(str(e.response.content, 'utf8'))


if __name__ == '__main__':
    main(sys.argv)
