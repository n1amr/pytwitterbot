#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import time
import tweepy

from pytwitterbot.authenticator import Authenticator
from pytwitterbot.config import Config
from pytwitterbot.favorite_saver_bot import FavoriteSaverBot
from pytwitterbot.retweet_bot import RetweetBot
from pytwitterbot.saver_bot import SaverBot
from pytwitterbot.tweet_bot import TweetBot


THIS_DIR = os.path.abspath(os.path.dirname(__file__))

log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('bot_home', type=str, default=None)

    args = parser.parse_args()

    if args.bot_home is None:
        args.bot_home = os.path.join(os.path.expanduser('~'), '.pytwitterbot')
    args.bot_home = os.path.abspath(args.bot_home)

    return args


def main(args: argparse.Namespace):
    log.info(f'Args: {args}')

    bot_home = args.bot_home

    log.info(f'Started in directory {bot_home}')

    config = Config(bot_home)
    authenticator = Authenticator(config, retry=True)
    twitter = authenticator.get_api_client()
    screen_name = twitter.get_settings()['screen_name']
    auth_user = twitter.get_user(screen_name=screen_name)

    log.info(f'Signed in as: {auth_user.name} (@{auth_user.screen_name})')

    bots = create_bots(twitter, auth_user, config)
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


def create_bots(twitter, auth_user: tweepy.User, config: Config):
    settings = config.settings

    bots = []

    if settings.get('bots.tweet.enabled', True):
        bots.append(TweetBot(twitter, auth_user, config))
    if settings.get('bots.retweet.enabled', True):
        bots.append(RetweetBot(twitter, auth_user, config))
    if settings.get('bots.saver.enabled', False):
        bots.append(SaverBot(twitter, auth_user, config))
    if settings.get('bots.favorite_saver.enabled', False):
        bots.append(FavoriteSaverBot(twitter, auth_user, config))

    return bots


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
    log_file = os.path.abspath(os.path.join(args.bot_home, 'log'))
    setup_logging(log_file)
    try:
        sys.exit(main(args))
    except Exception as e:
        log.exception(e)
        sys.exit(1)


if __name__ == '__main__':
    entry_point()
