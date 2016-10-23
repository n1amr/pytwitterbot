from pytwitterbot.file_helper import load_file_lines
from math import ceil
import subprocess


class TweetBot(object):

    def __init__(self, client):
        super(TweetBot, self).__init__()
        self.client = client
        self.commands = load_file_lines('commands')

    def start(self):
        for command in self.commands:
            print(command)
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                shell=True)
            out, err = process.communicate()
            msg = str(out, 'utf8').rstrip()
            try:
                print('=' * 50)
                print('$', command)
                print('Tweeting')
                if len(msg) <= 140:
                    print(msg)
                    self.client.update_status(msg)
                else:
                    for m in split(msg, 140, 3):
                        print(m)
                        self.client.update_status(m)
                print('=' * 50)
            except Exception as e:
                print(e)


def split(s, max_size, dots_size=3):
    n = len(s)
    if n <= max_size:
        yield s

    s1 = s[:dots_size]
    s2 = s[-dots_size:]
    s = s[dots_size: -dots_size]
    dots = '.' * dots_size

    max_size -= dots_size * 2
    n -= dots_size
    for i in range(ceil(n / max_size)):
        yield (s1 if i == 0 else dots) + \
            s[i * max_size: (i + 1) * max_size] + \
            (s2 if i == ceil(n / max_size) - 1 else dots)