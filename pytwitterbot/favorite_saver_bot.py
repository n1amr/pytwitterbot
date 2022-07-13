from glob import iglob
from hashlib import md5
import json
import logging
import os
import re
from statistics import median_grouped
import requests
import time
import tqdm
import tweepy

from tweepy.models import Status
from typing import Dict, Iterable, List, Tuple

from pytwitterbot.config import Config
from pytwitterbot.file_utils import (
    ensure_parent_dir,
    load_text,
    write_text,
)


log = logging.getLogger(__name__)

TWEETS_INDEX_HEADER = 'var tweet_index = '

MAX_TWEETS_TO_FETCH = 100

RETRY_COUNT = 20
RETRY_DELAY_SECONDS = 5
TWEET_COUNT_PER_FETCH = 5


class FavoriteSaverBot:
    def __init__(self, twitter: tweepy.API, auth_user: tweepy.User, config: Config):
        self.config = config
        self.twitter = twitter
        self.bot_user = auth_user
        self.bot_user_id = self.bot_user.id_str

        self.marked_as_saved = self.config.marked_as_saved

        self.settings = self.config.settings['bots.favorite_saver.config']
        self.root_path = self.settings['root_path']

        self.max_tweets_to_fetch = self.settings.get('max_tweets_to_fetch', MAX_TWEETS_TO_FETCH)

    def start(self):
        fill_md5sum_cache(self.root_path)

        for year, month in sorted(existing_partition_keys, reverse=True):
            key = (year, month)

            log.info(f'Downloading media for partition {key}.')

            partition_tweets = self.load_partition(year, month)
            adjusted_partition_tweets = self.download_media_and_adjust_urls(partition_tweets, year, month)
            partition_tweets = adjusted_partition_tweets

            partitioned_new_tweets = {key: partition_tweets}

            self.merge_new_tweets(partitioned_new_tweets)

            try:
                pass
            except Exception as e:
                log.error(f'Cannot load {key}')
                log.exception(e)
                raise

        breakpoint()

        exit(0)  # TODO

        log.info(f'Fetching tweets')
        new_tweets = self.fetch_new_tweets()
        log.info(f'Fetched {len(new_tweets)} new tweets.')

        log.info('Downloading media')
        new_tweets = self.download_media_and_adjust_urls(new_tweets)

        partitioned_new_tweets = self.partition_by_month(new_tweets)

        self.merge_new_tweets(partitioned_new_tweets)

    def fetch_new_tweets(self) -> List[Status]:
        use_cursor = True
        if use_cursor:
            tweets_iterable = tweepy.Cursor(
                self.twitter.get_favorites,
                count=TWEET_COUNT_PER_FETCH,
                include_entities=True,
            ).items()
        else:
            tweets_iterable = iter(self.twitter.get_favorites(count=TWEET_COUNT_PER_FETCH))

        found_saved = 0

        fetched_tweets = []
        new_tweets = []
        while len(fetched_tweets) < self.max_tweets_to_fetch:
            tweet = None
            for trial in range(RETRY_COUNT):
                try:
                    if use_cursor:
                        tweet = tweets_iterable.next()
                    else:
                        tweet = next(tweets_iterable)
                    break
                except StopIteration as e:
                    break
                except Exception as e:
                    log.exception(e)
                    log.error(e)
                    log.error(f'Next trial: {trial + 2}')

                    if trial < RETRY_COUNT - 1:
                        time.sleep(RETRY_DELAY_SECONDS)
                    else:
                        raise

            if tweet is None:
                log.debug(f'Failed to fetch next tweet. Tweet is None.')
                break

            log.debug(f'Fetched tweet. {_summarize_tweet(tweet)}')
            fetched_tweets.append(tweet)

            id = tweet.id_str
            if id in self.marked_as_saved and False:  # TODO
                found_saved += 1
                log.debug(f'Found a saved tweet. Id: {id}. Found saved: {found_saved}.')
                if found_saved >= 20:
                    break
            else:
                log.info(f'Found new tweet. {_summarize_tweet(tweet)}.')
                new_tweets.append(tweet)
                if found_saved != 0:
                    log.warning(f'Found a new tweet {id} tweet after {found_saved} saved tweets.')

        return new_tweets

    def get_tweets_partition_path(self, year: int, month: int):
        return os.path.join(self.root_path, 'data', 'js', 'tweets', f'{year:04}_{month:02}.js')

    def get_tweets_index_path(self):
        return os.path.join(self.root_path, 'data', 'js', 'tweet_index.js')

    def load_partition(self, year: int, month: int) -> List[Status]:
        tweets = []

        partition_path = self.get_tweets_partition_path(year, month)

        if not os.path.exists(partition_path):
            log.warning(f'Could not load tweets from partition path: {partition_path}.')
            return tweets

        log.info(f'Loading tweets partition for {year:04}/{month:02} from: {partition_path}.')

        expected_header = _partition_header(year, month)

        all_text_content = load_text(partition_path)
        assert all_text_content.startswith(expected_header), all_text_content[:len(expected_header) * 2]

        text_json_content = all_text_content[len(expected_header):]

        data = json.loads(text_json_content)

        tweets = Status.parse_list(self.twitter, data)

        log.info(f'Loaded {len(tweets)} tweets partition for {year:04}/{month:02}.')

        return tweets

    def download_media_and_adjust_urls(self, tweets: List[Status], year: int, month: int) -> List[Status]:
        new_tweets = []
        for tweet in tqdm.tqdm(tweets, desc=f'Downloading media {year:04}/{month:02}.'):
            tweet_json = json.loads(json.dumps(tweet._json))
            self.visit_media_urls(tweet_json)
            new_tweet = Status.parse(self.twitter, tweet_json)
            new_tweets.append(new_tweet)

        return new_tweets

    def visit_media_urls(self, json_data):
        # TODO: Enable.
        keys_to_extract = [
            'profile_image_url',
            'profile_image_url_https',
            'media_url',
            'media_url_https',
        ]

        if isinstance(json_data, list):
            for item in json_data:
                self.visit_media_urls(item)

        elif isinstance(json_data, dict):
            keys = list(json_data.keys())
            for key in keys:
                value = json_data[key]

                if key == 'variants':
                    self.visit_best_variants(value)
                    continue

                if isinstance(value, str):
                    should_download = (
                        key in keys_to_extract
                        or key == 'url' and (
                            'pbs.twimg' in value
                            or 'video.twimg.com' in value and '.mp4' in value
                        )
                    )
                    if should_download:
                        media_url = value
                        backup_key = f'__backup__{key}'
                        if value.startswith('http'):
                            json_data[backup_key] = media_url

                        local_url = self.download_media_url(media_url)
                        json_data[key] = local_url
                else:
                    self.visit_media_urls(value)

    def visit_best_variants(self, variants: list):
        assert len(variants) > 0

        # Select best variant.
        best_variant = None
        best_bitrate = -1
        for variant in variants:
            url = variant['url']
            if '.mp4' not in url:
                continue
            bitrate = variant.get('bitrate', 0)
            if bitrate > best_bitrate:
                best_variant = variant
                best_bitrate = bitrate

        selected_variant = best_variant or variants[0]

        # Adjust best variant.
        for variant in variants:
            if variant != selected_variant:
                continue

            for key in list(variant.keys()):
                value = variant[key]
                if 'url' in key:
                    adjusted_url = self.download_media_url(value)
                    backup_key = f'__backup__{key}'
                    variant[key] = adjusted_url
                    if value.startswith('http'):
                        variant[backup_key] = value

    def download_media_url(self, media_url: str) -> str:
        if not media_url.startswith('http'):
            return media_url

        local_relpath = re.sub(r'^https?://', '', media_url)
        local_relpath = re.sub(r'\?.*$', '', local_relpath)
        # local_relpath = f'data/media/tweepy/{local_relpath}'
        local_relpath = f'data/media/legacy/retrospective/{local_relpath}'
        # local_relpath = f'data/media/legacy/original/{local_relpath}'

        local_path = os.path.join(self.root_path, local_relpath)

        if os.path.isfile(local_path):
            return local_relpath

        # http_media_url = f'http://{relpath}'
        log.info(f'Downloading {media_url} to {local_path}.')

        response = None

        for trial in range(RETRY_COUNT):
            try:
                response = requests.get(media_url)

                if response.status_code in [403, 404]:
                    return media_url

                response.raise_for_status()
                data = response.content

                _write(data, local_path)
                break
            except Exception as e:
                log.exception(e)
                log.error(e)
                if response is not None:
                    log.warning(response.status_code)

                if trial >= RETRY_COUNT - 1:
                    log.exception(e)
                    return media_url

        return local_relpath

    def partition_by_month(self, tweets: Iterable[Status]) -> Dict[Tuple[int, int], List[Status]]:
        partitioned_tweets = {}

        for tweet in tweets:
            dt = tweet.created_at
            key = (dt.year, dt.month)
            partitioned_tweets.setdefault(key, []).append(tweet)

        return partitioned_tweets

    def merge_new_tweets(self, partitioned_new_tweets: Dict[Tuple[int, int], List[Status]]):
        for (year, month), new_tweets in partitioned_new_tweets.items():
            partition_tweets = self.load_partition(year, month)

            new_partition_tweets = new_tweets + partition_tweets
            new_partition_tweets = _deduplicate_tweets(new_partition_tweets)
            new_partition_tweets = _sort_tweets(new_partition_tweets)

            self.store_tweets(new_partition_tweets, year, month)

            for tweet in new_partition_tweets:
                self.config.mark_saved(tweet.id_str)

        self.config.commit_saved_marks()

    def store_tweets(self, tweets: List[Status], year: int, month: int):
        partition_path = self.get_tweets_partition_path(year, month)

        json_tweets = [tweet._json for tweet in tweets]

        write_json_with_header(json_tweets, partition_path, header=_partition_header(year, month))
        # write_json(json_tweets, f'{partition_path}.gitignored.json')

        new_partition_metadata = {
            'tweet_count': len(tweets),
            'month': month,
            'year': year,
            'file_name': f'data/js/tweets/{year:04}_{month:02}.js',
            'var_name': f'tweets_{year:04}_{month:02}',
        }

        index_path = self.get_tweets_index_path()
        if os.path.isfile(index_path):
            partitions_metadata = load_json_with_header(index_path, header=TWEETS_INDEX_HEADER)
        else:
            partitions_metadata = []

        key_to_metadata = {}
        for metadata in partitions_metadata + [new_partition_metadata]:
            key = (metadata['year'], metadata['month'])
            key_to_metadata[key] = metadata

        partitions_metadata = [
            kv[1]
            for kv in sorted(key_to_metadata.items(), key=lambda kv: kv[0], reverse=True)
        ]

        write_json_with_header(partitions_metadata, index_path, header=TWEETS_INDEX_HEADER)
        # write_json(partitions_metadata, f'{index_path}.gitignored.json')

        log.info(f'Saved {len(tweets)} tweets for partition {year:04}/{month:02}.')


def _write(data: bytearray, path: str):
    ensure_parent_dir(path)
    with open(path, 'wb') as f:
        f.write(data)


def _sort_tweets(tweets):
    def _tweet_sort_key(tweet: Status):
        return (
            tweet.created_at,
            tweet.id,
            tweet.id_str,
        )

    return list(sorted(tweets, key=_tweet_sort_key, reverse=True))


def _deduplicate_tweets(tweets):
    stored_ids = set()
    result = []
    for tweet in tweets:
        id = tweet.id_str
        if id not in stored_ids:
            result.append(tweet)
            stored_ids.add(id)
    return result


def _partition_header(year: int, month: int) -> str:
    return f'Grailbird.data.tweets_{year:04}_{month:02} = '


def load_json_with_header(path, header):
    content = load_text(path)
    assert content.startswith(header), content[:len(header) * 2]

    json_text = content[len(header):]
    data = json.loads(json_text)

    return data


def write_json_with_header(data, path, header, *, indent=2):
    json_text = json.dumps(data, indent=indent, ensure_ascii=False)
    content = f'{header}{json_text}'

    write_text(content, path)


def _summarize_tweet(tweet: Status) -> str:
    escaped_text = tweet.text.replace("\n", "<NL>")

    return (
        f'Id: {tweet.id_str}' +
        f'. Created_at: {tweet.created_at}' +
        f'. User: {tweet.user.screen_name}' +
        f'. Text: {escaped_text}'
    )


existing_partition_keys = [
    (2010, 6),
    (2011, 3),
    (2011, 8),
    (2011, 10),
    (2011, 11),
    (2011, 12),
    (2012, 1),
    (2012, 2),
    (2012, 3),
    (2012, 4),
    (2012, 5),
    (2012, 6),
    (2012, 7),
    (2012, 8),
    (2012, 9),
    (2012, 10),
    (2012, 11),
    (2012, 12),
    (2013, 1),
    (2013, 3),
    (2013, 4),
    (2013, 5),
    (2013, 6),
    (2013, 7),
    (2013, 8),
    (2013, 9),
    (2013, 10),
    (2013, 11),
    (2013, 12),
    (2014, 1),
    (2014, 2),
    (2014, 3),
    (2014, 4),
    (2014, 5),
    (2014, 6),
    (2014, 7),
    (2014, 8),
    (2014, 9),
    (2014, 10),
    (2014, 11),
    (2014, 12),
    (2015, 1),
    (2015, 2),
    (2015, 3),
    (2015, 4),
    (2015, 5),
    (2015, 6),
    (2015, 7),
    (2015, 8),
    (2015, 9),
    (2015, 10),
    (2015, 11),
    (2015, 12),
    (2016, 1),
    (2016, 2),
    (2016, 3),
    (2016, 4),
    (2016, 5),
    (2016, 6),
    (2016, 7),
    (2016, 8),
    (2016, 9),
    (2016, 10),
    (2016, 11),
    (2016, 12),
    (2017, 1),
    (2017, 2),
    (2017, 3),
    (2017, 4),
    (2017, 5),
    (2017, 6),
    (2017, 8),
    (2017, 9),
    (2017, 11),
    (2017, 12),
    (2018, 1),
    (2018, 3),
    (2018, 4),
    (2018, 5),
    (2018, 6),
    (2018, 7),
    (2018, 8),
    (2018, 9),
    (2018, 10),
    (2018, 11),
    (2018, 12),
    (2019, 2),
    (2019, 3),
    (2019, 4),
    (2019, 7),
    (2019, 8),
    (2019, 9),
    (2019, 10),
    (2019, 11),
    (2019, 12),
    (2020, 1),
    (2020, 2),
    (2020, 3),
    (2020, 4),
    (2020, 5),
    (2020, 6),
    (2020, 7),
    (2020, 8),
    (2020, 9),
    (2020, 10),
    (2020, 11),
    (2020, 12),
    (2021, 1),
    (2021, 2),
    (2021, 3),
    (2021, 4),
    (2021, 5),
    (2021, 6),
    (2021, 7),
    (2021, 8),
    (2021, 9),
    (2021, 10),
    (2021, 11),
    (2021, 12),
    (2022, 1),
    (2022, 2),
    (2022, 3),
    (2022, 4),
    (2022, 5),
    (2022, 6),
]

# existing_partition_keys = [
#     (2014, 11),
# ]

md5sum_cache: Dict[str, List[str]] = {}


def fill_md5sum_cache(root_path):
    for path in iglob(root_path + '/data/media/legacy/retrospective/**', recursive=True):
        if os.path.isdir(path):
            continue
        relpath = os.path.relpath(path, root_path)
        hash = calculate_file_hash(path)
        md5sum_cache[hash] = os.path.relpath(path, root_path)
        # print(md5sum_cache)
        # exit(0)


def calculate_file_hash(path):
    with open(path, 'rb') as f:
        bytes = f.read()
        assert not len(f.read())

    hash = md5(bytes).hexdigest()
    return hash


def is_identical_file(path, reference_path):
    with open(path, 'rb') as f:
        bytes = f.read()
        assert not len(f.read())

    with open(reference_path, 'rb') as f:
        reference_bytes = f.read()
        assert not len(f.read())

    return bytes == reference_bytes


active_paths = set()
