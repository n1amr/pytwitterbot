_all_files = {}

ACCESS_TOKEN_KEYS = 'ACCESS_TOKEN_KEYS'
SEARCH_FOR = 'SEARCH_FOR'
REPLIES = 'REPLIES'
MARKED_AS_REPLIED = 'MARKED_AS_REPLIED'
MARKED_AS_RETWEETED = 'MARKED_AS_RETWEETED'
MUTED_TEXT = 'MUTED_TEXT'
MUTED_USER_IDS = 'MUTED_USER_IDS'
COMMANDS = 'COMMANDS'


def init(home):
    global _all_files
    _all_files = {
        ACCESS_TOKEN_KEYS: home + '/keys.json',
        SEARCH_FOR: home + '/search-for.txt',
        REPLIES: home + '/replies.txt',
        MARKED_AS_REPLIED: home + '/marked-as-replied.dat',
        MARKED_AS_RETWEETED: home + '/marked-as-retweeted.dat',
        MUTED_TEXT: home + '/muted-text.txt',
        MUTED_USER_IDS: home + '/muted-users-ids.txt',
        COMMANDS: home + '/commands.txt',
    }


def get_all_files():
    return _all_files


def get(name):
    if name in _all_files:
        return _all_files[name]
    return None
