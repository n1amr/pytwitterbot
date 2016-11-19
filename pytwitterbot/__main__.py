import os
import sys

from pytwitterbot import data_files
from pytwitterbot import file_helper
from pytwitterbot.retweet_bot import RetweetBot
from pytwitterbot.tweet_bot import TweetBot
from pytwitterbot.twitter_session import TwitterSession


def main(args):
    try:
        if len(args) > 1:
            root = args[1]
        else:
            root = os.environ['HOME'] + '/.pytwitterbot'

        print('started in', root if root.startswith('/') else './' + root)

        data_files.init(root)
        file_helper.assert_all_files()
        session = TwitterSession()

        print('signed in as @', session.twitter_client.me().name, sep='')

        bots = [TweetBot(session.twitter_client),
                RetweetBot(session.twitter_client)]

        for bot in bots:
            try:
                bot.start()
            except Exception as e:
                print(str(e.response.content, 'utf8'))

        print('done')
        return 0
    except KeyboardInterrupt:
        return 1


def entry_point():
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
