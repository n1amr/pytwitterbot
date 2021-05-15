from pytwitterbot import data_files
from pytwitterbot.file_helper import load_file_lines, load_queries_file


class ReplyBot(object):
    def __init__(self, client):
        super(ReplyBot, self).__init__()
        self.client = client
        self.queries = load_queries_file(data_files.SEARCH_FOR)
        self.replies = load_file_lines(data_files.REPLIES)
        self.marked_as_replied = load_file_lines(data_files.MARKED_AS_REPLIED)
        self.bot_user_id = client.me().id_str
