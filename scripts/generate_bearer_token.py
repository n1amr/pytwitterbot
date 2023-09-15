import os
import tweepy

client_id = os.environ['TWITTER_CLIENT_ID']
client_secret = os.environ['TWITTER_CLIENT_SECRET']

oauth2_user_handler = tweepy.OAuth2UserHandler(
    client_id=client_id,
    redirect_uri="https://localhost:3000/",
    # https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code
    scope=[
        'tweet.read',
        'tweet.write',
        'tweet.moderate.write',
        'users.read',
        'follows.read',
        'follows.write',
        'offline.access',
        'space.read',
        'mute.read',
        'mute.write',
        'like.read',
        'like.write',
        'list.read',
        'list.write',
        'block.read',
        'block.write',
        'bookmark.read',
        'bookmark.write',
    ],
    client_secret=client_secret,
)

breakpoint()

authorization_url = oauth2_user_handler.get_authorization_url()
print(authorization_url)
print('Paste redirection URL: ', end='')
redirection_url = input().strip()
token = oauth2_user_handler.fetch_token(redirection_url)
bearer_token = token['access_token']
print(token)
print(bearer_token)
