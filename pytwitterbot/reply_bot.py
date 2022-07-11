import tweepy

from pytwitterbot import tweet_bot
from pytwitterbot.config import Config


class ReplyBot:
    def __init__(self, twitter: tweepy.API, auth_user: tweepy.User, config: Config):
        super(ReplyBot, self).__init__()

        self.twitter = twitter
        self.bot_user_id = auth_user.id_str

        self.queries = config.queries
        self.replies = config.replies
        self.marked_as_replied = config.marked_as_replied
