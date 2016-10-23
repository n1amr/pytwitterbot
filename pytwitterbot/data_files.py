_all_files = {}


def init(home):
    global _all_files
    _all_files = {
        'access_token_keys': home + '/keys.json',
        'search_for': home + '/search-for.txt',
        'replies': home + '/replies.txt',
        'marked_as_replied': home + '/marked-as-replied.dat',
        'marked_as_retweeted': home + '/marked-as-retweeted.dat',
        'muted_text': home + '/muted-text.txt',
        'muted_user_ids': home + '/muted-users-ids.txt',
        'commands': home + '/commands.txt',
    }


def get_all_files():
    return _all_files


def get(name):
    if name in _all_files:
        return _all_files[name]
    return None
