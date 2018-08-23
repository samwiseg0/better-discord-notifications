#!/usr/bin/env python3
import os
import logging
import sys
import json
import datetime
import re
import requests
from imdb import IMDb
import script_config

discord_headers = {'content-type': 'application/json'}

# Set up the log file
log_filename = os.path.join(os.path.dirname(sys.argv[0]), 'radarr_notification.log')
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger('Radarr')

def get_imdb_rating(imdb_id):
    imdb_id = imdb_id.replace('tt', '')
    imdb_lookup = IMDb()
    imdb_data = imdb_lookup.get_movie(imdb_id)
    return imdb_data.get('rating')

def utc_now_iso():
    utcnow = datetime.datetime.utcnow()
    return utcnow.isoformat()

TEST_MODE = False

#Get ENV variables
movie_id = os.environ.get('radarr_movie_id')
if not movie_id:
    TEST_MODE = True

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
    scene_name = 'THIS IS A TEST MESSAGE'

    year = '2014'

#Get Trailer Link from Radarr
try:
    trailer_link = 'https://www.youtube.com/watch?v={}'.format(radarr_data['youTubeTrailerId'])
except:
    trailer_link = 'None'

title_slug = re.sub(r'[?|$|.|!|:]', r'', media_title).replace(' ', '-')

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
    release = moviedb_api_data['movie_results'][0]['release_date']
except:
    release = 'None'

#Get Poster from TMDB
poster_path = moviedb_api_data['movie_results'][0]['poster_path']

try:
    poster_path = 'https://image.tmdb.org/t/p/w185' + poster_path
except TypeError:
    #Send a generic poster if there is not one for this movie
    poster_path = 'https://i.imgur.com/GoqfZJe.jpg'

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
            'url': '{}movies/{}-{}'.format(script_config.radarr_url, title_slug.lower(), radarr_id),
            'image': {
                'url': poster_path
            },
            'fields': [
                {
                    'name': 'Quality',
                    'value': quality,
                    'inline': True
                },
                {
                    'name': 'Release Date',
                    'value': release,
                    'inline': True
                }
            ]
        },
        {
            'title': 'Overview',
            'color': 3381708,
            'description': overview
        },
        {
            'title': 'Trailer',
            'color': 3394662,
            'description': trailer_link,
        },
        {
            'title': 'IMDb URL',
            'color': 13421619,
            'description': imdb_url,
            'footer': {
                'text': '{}'.format(scene_name)
            },
            'timestamp': utc_now_iso()
        }

    ]
}

# Log json
log.info(json.dumps(message, sort_keys=True, indent=4, separators=(',', ': ')))

# Send notification
sender = requests.post(script_config.radarr_discord_url, headers=discord_headers, json=message)

# Log response from discord
log.info(sender.content)
