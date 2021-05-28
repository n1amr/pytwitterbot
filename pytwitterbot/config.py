import os

from typing import Any, Dict, Sequence, Set

from pytwitterbot.file_utils import (
    load_commentable_file,
    load_json,
    load_text_lines,
    touch_file,
    write_text_lines,
    write_text,
    write_json,
)


class Config:
    def __init__(self, bot_home: str):
        self.bot_home = os.path.abspath(bot_home)

        self.access_token_path = self._abspath('keys.json', create=False)

        self.settings: Dict[Any] = load_json(self._abspath('settings.json', default={}))

        self.commands: Sequence[str] = load_commentable_file(self._abspath('commands.txt'))
        self.queries: Sequence[str] = load_commentable_file(self._abspath('search-for.txt'))
        self.replies: Sequence[str] = load_commentable_file(self._abspath('replies.txt'))

        self.muted_text: Set[str] = set(load_commentable_file(self._abspath('muted-text.txt')))
        self.muted_user_ids: Set[str] = set(load_commentable_file(self._abspath('muted-users-ids.txt')))
        self.muted_usernames: Set[str] = set(load_commentable_file(self._abspath('muted-users.txt')))

        self.marked_as_retweeted_path = self._abspath('marked-as-retweeted.dat')
        self.marked_as_retweeted: Set[str] = set(load_text_lines(self.marked_as_retweeted_path))

        self.marked_as_saved_path = self._abspath('marked-as-saved.dat')
        self.marked_as_saved: Set[str] = set(load_text_lines(self.marked_as_saved_path))

        # TODO: WIP
        self.marked_as_replied_path = self._abspath('marked-as-replied.dat')
        self.marked_as_replied: Set[str] = set(load_text_lines(self.marked_as_replied_path))

        self.tweets_count_per_search = 30
        self.max_tweet_length = 280

    def _abspath(self, filename, create: bool = True, default: Any = None):
        path = os.path.join(self.bot_home, filename)
        if not os.path.isfile(path) and create:
            if default is not None:
                _, ext = os.path.splitext(path)
                ext = ext.lower()
                if ext == '.json':
                    write_json(default, path)
                else:
                    write_text(default, path)
            else:
                touch_file(path)
        return path

    def mark_retweeted(self, tweet_id):
        self.marked_as_retweeted.add(tweet_id)

    def commit_retweeted_marks(self):
        write_text_lines(
            list(sorted(map(str, self.marked_as_retweeted))),
            self.marked_as_retweeted_path,
        )

    def mark_saved(self, tweet_id):
        self.marked_as_saved.add(tweet_id)

    def commit_saved_marks(self):
        write_text_lines(
            list(sorted(map(str, self.marked_as_saved))),
            self.marked_as_saved_path,
        )
