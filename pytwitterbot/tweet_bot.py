import logging
import math
import subprocess

from pytwitterbot import data_files
from pytwitterbot.file_helper import load_file_lines

log = logging.getLogger(__name__)

MAX_TWEET_LENGTH = 280


class TweetBot(object):
    def __init__(self, client):
        super(TweetBot, self).__init__()
        self.client = client
        self.commands = load_file_lines(data_files.COMMANDS)

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

            if not len(output):
                log.warning(f'Command printed no output')
                continue

            log.info(f'Command output:\n{output}')
            tweet_text = output.strip()

            try:
                for chunk in chunk_text(tweet_text, MAX_TWEET_LENGTH, 3):
                    log.info(f'Will tweet:\n{chunk}')
                    self.client.update_status(chunk)
            except Exception as e:
                log.error(e)
                log.exception(e)


def chunk_text(text, max_size: int, dots_size: int = 3):
    length = len(text)

    if length <= max_size:
        yield text
        return

    s1 = text[:dots_size]
    s2 = text[-dots_size:]
    text = text[dots_size:-dots_size]
    dots = '.' * dots_size

    max_size -= dots_size * 2
    length -= dots_size
    for i in range(int(math.ceil(length / max_size))):
        chunk = (
            (s1 if i == 0 else dots)
            + text[i * max_size: (i + 1) * max_size]
            + (s2 if i == math.ceil(length / max_size) - 1 else dots)
        )
        assert len(chunk) <= max_size, [len(chunk), max_size, chunk]
        yield chunk
