from pytwitterbot import file_helper
from pytwitterbot import data_files
from pytwitterbot.twitter_session import TwitterSession
from pytwitterbot.retweet_bot import RetweetBot
from pytwitterbot.tweet_bot import TweetBot
import sys


def main(args):
    root = None
    if len(args) > 1:
        root = args[1]
        print('started in ', root)

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

    return 0


def entry_point():
    raise SystemExit(main(sys.argv))

if __name__ == '__main__':
    entry_point()
