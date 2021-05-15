#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import tempfile
import time

from pytwitterbot import data_files
from pytwitterbot import file_helper
from pytwitterbot.retweet_bot import RetweetBot
from pytwitterbot.tweet_bot import TweetBot
from pytwitterbot.twitter_session import TwitterSession

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('bot_dir', type=str, default=None)

    args = parser.parse_args()

    if args.bot_dir is None:
        args.bot_dir = os.path.join(os.path.expanduser('~'), '.pytwitterbot')
    args.bot_dir = os.path.abspath(args.bot_dir)

    return args


def main(args: argparse.Namespace):
    log.info(f'Args: {args}')

    bot_dir = args.bot_dir

    log.info(f'Started in directory {bot_dir}')

    data_files.init(bot_dir)
    file_helper.assert_all_files()
    session = TwitterSession()

    log.info(f'Signed in as @{session.twitter_client.me().name}')

    bots = [
        TweetBot(session.twitter_client),
        RetweetBot(session.twitter_client),
    ]

    for bot in bots:
        try:
            bot.start()
        except Exception as e:
            try:
                response_text = str(e.response.content, 'utf-8')
                log.error(response_text)
            except:
                log.error(e)
            log.exception(e)

    log.info('Finished')

    return 0


def setup_logging(log_file: str):
    short_logging_format = '[%(asctime)s.%(msecs)03d] %(levelname)-s: %(message)s'
    long_logging_format = f'{short_logging_format} --- %(name)s at %(filename)s:%(lineno)d'
    time_format = '%Y-%m-%d %H:%M:%S'

    logging.basicConfig(
        format=short_logging_format,
        level=os.environ.get('LOGLEVEL', 'info').upper(),
        datefmt=time_format,
        stream=sys.stdout,
    )
    logging.Formatter.converter = time.gmtime

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(long_logging_format))
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    log.info(f'Logging to file: {log_file}')


def entry_point():
    args = parse_args()
    log_file = os.path.abspath(os.path.join(args.bot_dir, 'log'))
    setup_logging(log_file)
    try:
        sys.exit(main(args))
    except Exception as e:
        log.exception(e)
        sys.exit(1)


if __name__ == '__main__':
    entry_point()
