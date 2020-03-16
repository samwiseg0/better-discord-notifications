#!/usr/bin/env python3
import os
import logging
import sys
import json
import re
import requests
import script_config
from datetime import datetime

discord_headers = {'content-type': 'application/json'}

# Set up the log file
log_filename = os.path.join(os.path.dirname(sys.argv[0]), 'radarr_notification.log')
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger('Radarr')

def get_profile_name(profile_id):
    try:
        get_profiles = requests.get('{}api/profile/{}?apikey={}'.format(script_config.radarr_url, profile_id, script_config.radarr_key)).json()
    except Exception as ex:
        log.error('Could not pull profile from radarr! ({})'.format(ex))

    try:
        profile_name = get_profiles['name']

    except Exception as ex:
        log.error('Could not find profile ID in radarr! ({})'.format(ex))
        profile_name = 'Unknown'

    return profile_name

def get_imdb_rating(imdb_id):
    get_imdb = requests.get('https://imdb-api.com/API/Ratings/{}/{}'.format(script_config.radarr_imdbapi_key, imdb_id)).json()
    imdb_rating = get_imdb['imDb']
    if not imdb_rating:
            imdb_rating = "Unknown"
    return imdb_rating

def utc_now_iso():
    utcnow = datetime.utcnow()
    return utcnow.isoformat()

# Get Event Type
eventtype = os.environ.get('radarr_eventtype')

if eventtype == 'test':
    TEST_MODE = True
else:
    TEST_MODE = False

#Get ENV variables
movie_id = os.environ.get('radarr_movie_id')
if not movie_id:
    movie_id = 10

media_title = os.environ.get('radarr_movie_title')
if not media_title:
    media_title = 'The Lego Movie'

imdb_id = os.environ.get('radarr_movie_imdbid')
if not imdb_id:
    imdb_id = 'tt1490017'

quality = os.environ.get('radarr_moviefile_quality')
if not quality:
    quality = 'Bluray-2160p'

scene_name = os.environ.get('radarr_moviefile_scenename')

imdb_rating = get_imdb_rating(imdb_id)

imdb_url = 'https://www.imdb.com/title/' + imdb_id

#Get Radarr data
radarr_api_url = '{}api/movie/{}?apikey={}'.format(script_config.radarr_url, movie_id, script_config.radarr_key)

radarr = requests.get(radarr_api_url)

radarr_data = radarr.json()

if not TEST_MODE:
    year = radarr_data['year']

if TEST_MODE:
    scene_name = 'A.Movie.2020.TrueHD.Atmos.AC3.MULTISUBS.UHD.4k.BluRay.x264.HQ-TUSAHD'
    year = '2014'

#Get Trailer Link from Radarr
try:
    trailer_link = 'https://www.youtube.com/watch?v={}'.format(radarr_data['youTubeTrailerId'])
except:
    trailer_link = 'None'

title_slug = re.sub(r'[?|$|.|!|:|/]', r'', media_title).replace(' ', '-')

#Get data from TMDB
moviedb_api_url = 'https://api.themoviedb.org/3/find/{}?api_key={}&external_source=imdb_id'.format(imdb_id, script_config.moviedb_key)

moviedb_api = requests.get(moviedb_api_url)

moviedb_api_data = moviedb_api.json()

radarr_id = moviedb_api_data['movie_results'][0]['id']

try:
    overview = moviedb_api_data['movie_results'][0]['overview']
except:
    overview = 'None'

try:
    physical_release =  radarr_data['physicalRelease']
    physical_release= datetime.strptime(physical_release,"%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y")
except:
    physical_release = 'None'

try:
    release = moviedb_api_data['movie_results'][0]['release_date']
    release = datetime.strptime(release, "%Y-%m-%d").strftime("%B %d, %Y")
except:
    release = 'None'

try:
    genres = json.dumps(radarr_data['genres'])
    genres = re.sub(r'[?|$|.|!|:|/|\]|\[|\"]', r'', genres)
except:
    genres = 'None'

quality_profile = get_profile_name(radarr_data['qualityProfileId'])

#Get Poster from TMDB
poster_path = moviedb_api_data['movie_results'][0]['poster_path']

try:
    poster_path = 'https://image.tmdb.org/t/p/w500' + poster_path
except TypeError:
    #Send a generic poster if there is not one for this movie
    poster_path = 'https://i.imgur.com/GoqfZJe.jpg'

# Format the message
message = {
    'username': script_config.radarr_discord_user,
    'content': 'New movie downloaded - {} ({}) IMDb: {}'.format(media_title, year, imdb_rating),
    'embeds': [
        {
            'author': {
                'name': 'Movies',
                'url': script_config.radarr_url,
                'icon_url': script_config.radarr_icon
            },
            'title': '{} ({})'.format(media_title, year),
            'color': 3394662,
            'url': '{}movie/{}-{}'.format(script_config.radarr_url, title_slug.lower(), radarr_id),
            'image': {
                'url': poster_path
            },
            'fields': [

            ]
        },
        {
            'title': 'Overview',
            'color': 3381708,
            'description': overview,
                "fields": [
                    {
                        "name": 'Quality',
                        "value": quality,
                        "inline": True
                    },
                    {
                        "name": 'Quality Profile',
                        "value": quality_profile,
                        "inline": True
                    },
                    {
                        "name": 'Release Date',
                        "value": release,
                        "inline": True
                    },
                    {
                        "name": 'Physical Release Date',
                        "value": physical_release,
                        "inline": True
                    },
                    {
                        "name": 'IMDb Rating',
                        "value": "[{}]({})".format(imdb_rating, imdb_url),
                        "inline": True
                    },
                    {
                        "name": 'Genres',
                        "value": genres,
                        "inline": True
                    },
                    {
                        "inline": False,
                        "name": "Trailer",
                        "value": trailer_link
                    }
                ],
                'footer': {
                    'text': '{}'.format(scene_name)
                },
                'timestamp': utc_now_iso()

        },

    ]
}

# Log json
log.info(json.dumps(message, sort_keys=True, indent=4, separators=(',', ': ')))

# Send notification
sender = requests.post(script_config.radarr_discord_url, headers=discord_headers, json=message)

# Log response from discord
log.info(sender.content)
