import logging
import tweepy

from pytwitterbot import api_keys
from pytwitterbot.config import Config
from pytwitterbot.file_utils import load_json, write_json

log = logging.getLogger(__name__)


class Authenticator:
    def __init__(self, config: Config, retry=True):
        super(Authenticator, self).__init__()

        self.config = config
        self.retry = retry

    def get_api_client(self) -> tweepy.API:
        auth = tweepy.OAuthHandler(
            api_keys.consumer_key,
            api_keys.consumer_secret,
        )
        auth.secure = True

        access_token = self._load_access_token()
        if access_token is None:
            access_token = self._request_access_token(auth)
            self._store_access_token(access_token)

        auth.set_access_token(
            access_token['access_token'],
            access_token['access_token_secret'],
        )

        kwargs = dict(
            wait_on_rate_limit=True,
        )
        if self.retry:
            kwargs.update(
                retry_count=20,
                retry_delay=3,
            )

        # https://docs.tweepy.org/en/v3.5.0/api.html
        twitter = tweepy.API(auth, **kwargs)
        return twitter

    def _request_access_token(self, auth):
        auth_url = auth.get_authorization_url()
        print(auth_url)
        print('Please visit previous URL and enter the code: ')
        pin = input('PIN: ').strip()
        auth.get_access_token(pin)

        access_token = {
            'access_token': auth.access_token,
            'access_token_secret': auth.access_token_secret,
        }
        return access_token

    def _store_access_token(self, access_token):
        write_json(access_token, self.config.access_token_path)

    def _load_access_token(self):
        access_token = None
        try:
            access_token = load_json(self.config.access_token_path)
        except Exception as e:
            log.error('Cannot load access token')
            log.exception(e)
        return access_token
