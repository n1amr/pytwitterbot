import logging
import math
import subprocess

import tweepy

from pytwitterbot.config import Config

log = logging.getLogger(__name__)


class TweetBot:
    def __init__(self, twitter: tweepy.API, config: Config):
        super(TweetBot, self).__init__()

        self.twitter = twitter
        self.config = config
        self.commands = config.commands

    def start(self):
        for command in self.commands:
            if command.strip().startswith('#'):
                continue

            log.info(f'Executing command: $ {command}')
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
                encoding='utf-8',
                universal_newlines=True,
            )
            output, error = process.communicate()
            if error:
                log.error(f'Error while executing command: {error}')

            log.info(f'Command output:\n{output}')

            tweet_text = output.strip()
            if not len(tweet_text):
                log.warning(f'Skipped tweeting an empty tweet')
                continue

            try:
                chunks = chunk_text(tweet_text, self.config.max_tweet_length)
                for chunk in chunks:
                    log.info(f'Will tweet:\n{chunk}')
                    self.twitter.update_status(chunk)
            except Exception as e:
                log.error(e)
                log.exception(e)


def chunk_text(text, max_length: int, dots_length: int = 3):
    if len(text) <= max_length:
        yield text
        return

    prefix = '.' * dots_length + ' '
    suffix = ' ' + '.' * dots_length
    assert max_length > len(prefix) + len(suffix)

    first_prefix = text[:len(prefix)]
    last_suffix = text[-len(suffix):]
    middle_text = text[len(prefix):-len(suffix)]
    middle_length = len(middle_text)
    max_content_length = max_length - (len(prefix) + len(suffix))

    chunks_count = int(math.ceil(middle_length / max_content_length))
    for i in range(chunks_count):
        chunk = ''.join((
            first_prefix if i == 0 else prefix,
            middle_text[i * max_content_length: (i + 1) * max_content_length],
            last_suffix if i == chunks_count - 1 else suffix,
        ))
        assert len(chunk) <= max_length, [len(chunk), max_length, chunk]
        assert len(chunk)
        yield chunk
