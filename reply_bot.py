import data_files
from file_helper import load_file_lines


class ReplyBot(object):

    def __init__(self, client):
        super(ReplyBot, self).__init__()
        self.client = client
        self.queries = load_file_lines('search_for')
        self.replies = load_file_lines('replies')
        self.marked_as_replied = load_file_lines('marked_as_replied')
        self.bot_user_id = client.me().id_str
