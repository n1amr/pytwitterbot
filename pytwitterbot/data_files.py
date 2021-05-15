import os

ACCESS_TOKEN_KEYS = 'ACCESS_TOKEN_KEYS'
SEARCH_FOR = 'SEARCH_FOR'
REPLIES = 'REPLIES'
MARKED_AS_REPLIED = 'MARKED_AS_REPLIED'
MARKED_AS_RETWEETED = 'MARKED_AS_RETWEETED'
MUTED_TEXT = 'MUTED_TEXT'
MUTED_USER_IDS = 'MUTED_USER_IDS'
MUTED_USERNAMES = 'MUTED_USERNAMES'
COMMANDS = 'COMMANDS'

FILE_NAMES = {
    ACCESS_TOKEN_KEYS: 'keys.json',
    SEARCH_FOR: 'search-for.txt',
    REPLIES: 'replies.txt',
    MARKED_AS_REPLIED: 'marked-as-replied.dat',
    MARKED_AS_RETWEETED: 'marked-as-retweeted.dat',
    MUTED_TEXT: 'muted-text.txt',
    MUTED_USER_IDS: 'muted-users-ids.txt',
    MUTED_USERNAMES: 'muted-users.txt',
    COMMANDS: 'commands.txt',
}

_all_files = {}


def init(home):
    global _all_files
    _all_files = {}
    for k, v in FILE_NAMES.items():
        _all_files[k] = os.path.join(home, v)


def get_all_files():
    return _all_files


def get(name):
    if name in _all_files:
        return _all_files[name]
    return None
