#!/usr/bin/env python3
import os
import logging
import sys
import json
import datetime
import requests
import script_config

discord_headers = {'content-type': 'application/json'}

# Set up the log file
log_filename = os.path.join(os.path.dirname(sys.argv[0]), 'sonarr_notification.log')
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s')
log = logging.getLogger('Sonarr')

def utc_now_iso():
    utcnow = datetime.datetime.utcnow()
    return utcnow.isoformat()

def main():
    # Get/set ENV variables
    eventtype = os.environ.get('sonarr_eventtype')

    season = os.environ.get('sonarr_episodefile_seasonnumber')

    episode = os.environ.get('sonarr_episodefile_episodenumbers')

    tvdb_id = os.environ.get('sonarr_series_tvdbid')

    scene_name = os.environ.get('sonarr_episodefile_scenename')

    media_title = os.environ.get('sonarr_series_title')

    episode_title = os.environ.get('sonarr_episodefile_episodetitles')

    quality = os.environ.get('sonarr_episodefile_quality')

    is_upgrade = os.environ.get('sonarr_isupgrade')

    overview = ''

    if eventtype == 'Test':
        log.info('Sonarr script test succeeded.')
        sys.exit(0)

    # Get show information from skyhook
    get_skyhook = requests.get(script_config.skyhook_url + str(tvdb_id))

    skyhook_data = get_skyhook.json()

    title_slug = skyhook_data['slug']

    # Get banner image for show
    try:
        banner = skyhook_data['seasons'][int(season)]['images'][1]['url']
    except Exception as ex:
        log.error(ex)
        banner = skyhook_data['images'][1]['url']

    for line in skyhook_data['episodes']:
        try:
            if int(line['seasonNumber']) == int(season) and \
                    int(line['episodeNumber']) == int(episode):

                if line['overview']:
                    overview = line['overview']

        except Exception as ex:
            log.error(ex)


    if not overview:
        overview = 'None'

    if len(str(season)) == 1:
        season = '0{}'.format(season)

    if len(str(episode)) == 1:
        episode = '0{}'.format(episode)

    if is_upgrade == 'True':
        content = 'Upgraded Episode - {}: {}'.format(media_title, episode_title)
        is_upgrade = 'Yes!'

    else:
        content = 'New episode downloaded - {}: {}'.format(media_title, episode_title)
        is_upgrade = 'Nope'


    message = {
        "username": script_config.sonarr_discord_user,
        "content": content,
        "embeds": [
            {
                "author": {
                    "name": "TV",
                    "url": script_config.sonarr_url,
                    "icon_url": script_config.sonarr_icon
                    },
                "title": "{}: {}".format(media_title, episode_title),
                "color": 3394662,
                "url": "{}series/{}".format(script_config.sonarr_url, title_slug),
                "image": {
                    "url": banner
                    },
                "fields": [
                    {
                        "name": "Episode",
                        "value": "s{}e{}".format(season, episode),
                        "inline": True
                    },
                    {
                        "name": "Quality",
                        "value": quality,
                        "inline": True
                    },
                    {
                        "name": "Upgrade?",
                        "value": is_upgrade,
                        "inline": True
                    }
                    ]
            },
            {
                "title": "Overview",
                "color": 3381708,
                "description": overview,
                "footer": {
                    "text": "{}".format(scene_name)
                    },
                "timestamp": utc_now_iso()
            }

        ]
    }

    log.info(json.dumps(message, sort_keys=True, indent=4, separators=(',', ': ')))

    # Send notification
    sender = requests.post(script_config.sonarr_discord_url, headers=discord_headers, json=message)

    # Log response
    log.info(sender.content)

# Call main
main()
