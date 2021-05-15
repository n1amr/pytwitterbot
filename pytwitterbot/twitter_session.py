import json
import logging
import tweepy

from pytwitterbot import api_keys
from pytwitterbot import data_files

log = logging.getLogger(__name__)


class TwitterSession(object):
    def __init__(self):
        super(TwitterSession, self).__init__()
        self.access_token = self.load_access_token()
        self.twitter_client = self.get_api_client()

    def request_access_token(self, auth):
        try:
            auth_url = auth.get_authorization_url()
            print(auth_url)
            print('Please visit previous URL and enter the code: ')
            pin = input('PIN: ').strip()
            auth.get_access_token(pin)

            self.access_token = {
                'access_token': auth.access_token,
                'access_token_secret': auth.access_token_secret}
            self.store_access_token()
        except tweepy.TweepError:
            log.error('Failed to get request token.')

    def get_api_client(self):
        auth = tweepy.OAuthHandler(
            api_keys.consumer_key,
            api_keys.consumer_secret,
        )
        auth.secure = True

        if self.access_token is None:
            self.request_access_token(auth)
        else:
            auth.set_access_token(
                self.access_token['access_token'],
                self.access_token['access_token_secret'])

        # https://docs.tweepy.org/en/v3.5.0/api.html
        twitter = tweepy.API(
            auth,
            wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True,
            # retry_count=10_000,
            # retry_delay=5,
        )
        return twitter

    def store_access_token(self):
        with open(data_files.get(data_files.ACCESS_TOKEN_KEYS), 'w') as file:
            file.write(json.dumps(self.access_token, indent=2, ensure_ascii=False))

    @staticmethod
    def load_access_token():
        access_token = None
        with open(data_files.get(data_files.ACCESS_TOKEN_KEYS), 'r') as file:
            json_text = file.read()
            try:
                access_token = json.loads(json_text)
            except:
                log.error('cannot load access token')
        return access_token
