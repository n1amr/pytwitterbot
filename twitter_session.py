import api_keys
import data_files
from json import dumps, loads
import json
import tweepy


class TwitterSession(object):

    def __init__(self):
        super(TwitterSession, self).__init__()
        self.access_token = self.load_access_token()
        self.twitter_client = self.get_api_client()

    def request_access_token(self, auth):
        try:
            auth_url = auth.get_authorization_url()
            print(auth_url)
            print('Please visit the URL and enter the code: ')
            pin = input('PIN: ').strip()
            auth.get_access_token(pin)

            self.access_token = {
                'access_token': auth.access_token,
                'access_token_secret': auth.access_token_secret}
            self.store_access_token()
        except tweepy.TweepError:
            print('Error! Failed to get request token.')

    def get_api_client(self):
        auth = tweepy.OAuthHandler(
            api_keys.consumer_key,
            api_keys.consumer_secret)
        auth.secure = True

        if self.access_token is None:
            self.request_access_token(auth)
        else:
            auth.set_access_token(
                self.access_token['access_token'],
                self.access_token['access_token_secret'])

        twitter = tweepy.API(auth)
        return twitter

    def store_access_token(self):
        with open(data_files.access_token_keys, 'w') as file:
            file.write(dumps(self.access_token))

    @staticmethod
    def load_access_token():
        access_token = None
        with open(data_files.get('access_token_keys'), 'r') as file:
            json_text = file.read()
            try:
                access_token = loads(json_text)
            except json.decoder.JSONDecodeError:
                print('Cannot load access token')
        return access_token
