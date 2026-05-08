#!/usr/bin/python3
import os
import logging
import sys
import json
import requests
from datetime import datetime, timezone


# --- Logging setup ---

log_filename = os.path.join(os.path.dirname(sys.argv[0]), 'sonarr_notification.log')
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger('Sonarr')

DISCORD_HEADERS = {'content-type': 'application/json'}


# --- Helper functions ---

def parse_episode_numbers(value):
    return [int(x) for x in value.split(',') if x.strip().isdigit()]


def get_episode_overview(episodes, season, episode_num, fallback):
    for ep in episodes:
        try:
            if int(ep['seasonNumber']) == season and int(ep['episodeNumber']) == episode_num:
                return ep['overview'] if ep.get('overview') else fallback
        except Exception as ex:
            log.error(f'Failed to match episode from Skyhook: {ex}')
    return fallback


def get_last_download(cfg):
    url = f'{cfg.sonarr_url.rstrip("/")}/api/v3/history?pageSize=1&sortKey=date&sortDirection=descending&includeEpisode=true&includeSeries=true&apikey={cfg.sonarr_key}'
    log.info(f'Fetching Sonarr history from: {cfg.sonarr_url}')
    record = requests.get(url).json()['records'][0]
    return {
        'season':        str(record['episode']['seasonNumber']),
        'episode':       str(record['episode']['episodeNumber']),
        'tvdb_id':       str(record['series']['tvdbId']),
        'media_title':   record['series']['title'],
        'episode_title': record['episode'].get('title', ''),
        'quality':       record['quality']['quality']['name'],
        'scene_name':    record.get('sourceTitle', ''),
    }


def get_season_banner(skyhook_data, season):
    try:
        return skyhook_data['seasons'][season]['images'][1]['url']
    except Exception as ex:
        log.warning(f'Season banner not found, falling back to series banner: {ex}')
        return skyhook_data['images'][0]['url']


# --- Main ---

def run(cfg):
    TEST_MODE = os.environ.get('sonarr_eventtype', '').lower() == 'test'

    if TEST_MODE:
        try:
            last          = get_last_download(cfg)
            season        = last['season']
            episode       = last['episode']
            tvdb_id       = last['tvdb_id']
            media_title   = last['media_title']
            episode_title = last['episode_title']
            quality       = last['quality']
            scene_name    = last['scene_name']
            is_upgrade    = 'False'
        except Exception as ex:
            log.error(f'Could not fetch last download for test notification: {ex}')
            sys.exit(1)
    else:
        season        = os.environ.get('sonarr_episodefile_seasonnumber')
        episode       = os.environ.get('sonarr_episodefile_episodenumbers')
        tvdb_id       = os.environ.get('sonarr_series_tvdbid')
        scene_name    = os.environ.get('sonarr_episodefile_scenename') or ''
        media_title   = os.environ.get('sonarr_series_title')
        episode_title = os.environ.get('sonarr_episodefile_episodetitles')
        quality       = os.environ.get('sonarr_episodefile_quality')
        is_upgrade    = os.environ.get('sonarr_isupgrade')

    # Fetch show data from Skyhook
    try:
        skyhook_data = requests.get(f'{cfg.skyhook_url}{tvdb_id}', timeout=10).json()
    except Exception as ex:
        log.error(f'Could not fetch show data from Skyhook: {ex}')
        sys.exit(1)

    title_slug  = skyhook_data['slug']
    season_num  = int(season)

    episode_nums = parse_episode_numbers(episode)
    if not episode_nums:
        log.error(f'Could not parse episode numbers from: {episode!r}')
        sys.exit(1)
    episode_num = episode_nums[0]

    banner   = get_season_banner(skyhook_data, season_num)
    overview = get_episode_overview(
        skyhook_data['episodes'], season_num, episode_num, skyhook_data['overview']
    )

    season_str  = str(season_num).zfill(2)
    episode_str = str(episode_num).zfill(2)

    if is_upgrade == 'True':
        content      = f'Upgraded Episode - {media_title}: {episode_title}'
        upgrade_text = 'Yes!'
    else:
        content      = f'New episode downloaded - {media_title}: {episode_title}'
        upgrade_text = 'Nope'

    content_rating = skyhook_data.get('contentRating', 'None')
    network        = skyhook_data.get('network', 'None')
    genres         = ', '.join(skyhook_data.get('genres', [])) or 'None'

    # Build Discord message
    message = {
        'username': cfg.sonarr_discord_user,
        'content': content,
        'embeds': [
            {
                'author': {
                    'name': 'TV',
                    'url': cfg.sonarr_url,
                    'icon_url': cfg.sonarr_icon,
                },
                'title': f'{media_title}: {episode_title}',
                'color': 3394662,
                'url': f'{cfg.sonarr_url}series/{title_slug}',
                'image': {'url': banner},
            },
            {
                'title': 'Overview',
                'color': 3381708,
                'description': overview,
                'fields': [
                    {'name': 'Episode',        'value': f's{season_str}e{episode_str}', 'inline': True},
                    {'name': 'Quality',        'value': quality,                        'inline': True},
                    {'name': 'Upgrade?',       'value': upgrade_text,                   'inline': True},
                    {'name': 'Content Rating', 'value': content_rating,                 'inline': True},
                    {'name': 'Network',        'value': network,                        'inline': True},
                    {'name': 'Genres',         'value': genres,                         'inline': True},
                ],
                'footer': {'text': scene_name},
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        ],
    }

    # Send notification
    log.info(json.dumps(message, sort_keys=True, indent=4, separators=(',', ': ')))
    sender = requests.post(cfg.sonarr_discord_url, headers=DISCORD_HEADERS, json=message)
    log.info(sender.text)
