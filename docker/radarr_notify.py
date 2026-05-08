#!/usr/bin/python3
import os
import logging
import sys
import json
import re
import requests
from datetime import datetime, timezone


# --- Logging setup ---

log_filename = os.path.join(os.path.dirname(sys.argv[0]), 'radarr_notification.log')
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger('Radarr')

DISCORD_HEADERS = {'content-type': 'application/json'}


# --- Helper functions ---

def get_quality_profile(cfg, profile_id):
    try:
        url = f'{cfg.radarr_url}api/v3/qualityprofile/{profile_id}?apikey={cfg.radarr_key}'
        return requests.get(url).json()['name']
    except Exception as ex:
        log.error(f'Could not get quality profile from Radarr: {ex}')
        return 'Unknown'


def get_imdb_rating(imdb_id):
    try:
        data = requests.get(f'https://api.imdbapi.dev/titles/{imdb_id}').json()
        return str(data['rating']['aggregateRating'])
    except Exception as ex:
        log.error(f'Could not get IMDb rating from imdbapi.dev: {ex}')
        return '?'


def get_rt_score(cfg, imdb_id):
    try:
        url = f'https://www.omdbapi.com/?i={imdb_id}&apikey={cfg.radarr_imdbapi_key}'
        for rating in requests.get(url).json().get('Ratings', []):
            if rating['Source'] == 'Rotten Tomatoes':
                return rating['Value'].replace('%', '')
    except Exception as ex:
        log.error(f'Could not get Rotten Tomatoes score from OMDb: {ex}')
    return '?'


def get_tmdb_directors(cfg, tmdb_movie_id):
    try:
        url = f'https://api.themoviedb.org/3/movie/{tmdb_movie_id}/credits?api_key={cfg.moviedb_key}'
        crew = requests.get(url).json().get('crew', [])
        return ', '.join(p['name'] for p in crew if p['job'] == 'Director')
    except Exception as ex:
        log.error(f'Could not get director info from TMDb: {ex}')
        return 'Unknown'


def format_rt_score(score):
    if score == '?':
        return f'<:tomato_rot:690250277592367113> {score}'
    elif int(score) >= 60:
        return f'<:tomato_whole:689953229559300268> {score}%'
    else:
        return f'<:tomato_rot:690250277592367113> {score}%'


def human_size(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while nbytes >= 1000 and i < len(suffixes) - 1:
        nbytes /= 1000.0
        i += 1
    value = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return f'{value} {suffixes[i]}'


def rt_url_for(title):
    slug = re.sub(r'[^a-zA-Z0-9\s]', '', title).lower().replace(' ', '_')
    return f'https://www.rottentomatoes.com/m/{slug}'


# --- Main ---

def run(cfg):
    # Environment variables
    TEST_MODE   = os.environ.get('radarr_eventtype') == 'test'
    movie_id    = os.environ.get('radarr_movie_id')            or 10
    media_title = os.environ.get('radarr_movie_title')         or 'The Lego Movie'
    imdb_id     = os.environ.get('radarr_movie_imdbid')        or 'tt1490017'
    quality     = os.environ.get('radarr_moviefile_quality')   or 'Bluray-2160p'
    scene_name  = os.environ.get('radarr_moviefile_scenename') or ''

    # Fetch external data
    imdb_rating = get_imdb_rating(imdb_id)
    rt_score    = get_rt_score(cfg, imdb_id)

    radarr_data = requests.get(
        f'{cfg.radarr_url}api/v3/movie/{movie_id}?apikey={cfg.radarr_key}'
    ).json()

    tmdb_results = requests.get(
        f'https://api.themoviedb.org/3/find/{imdb_id}'
        f'?api_key={cfg.moviedb_key}&external_source=imdb_id'
    ).json()
    tmdb_movie    = tmdb_results['movie_results'][0]
    tmdb_movie_id = tmdb_movie['id']

    # Parse data
    if TEST_MODE:
        scene_name = 'A.Movie.2020.TrueHD.Atmos.AC3.MULTISUBS.UHD.4k.BluRay.x264.HQ-TUSAHD'
        year = '2014'
    else:
        year = radarr_data['year']

    try:
        trailer_link = f'https://www.youtube.com/watch?v={radarr_data["youTubeTrailerId"]}'
    except Exception:
        log.warning('Trailer ID missing from Radarr data')
        trailer_link = 'None'

    try:
        release = datetime.strptime(tmdb_movie['release_date'], '%Y-%m-%d').strftime('%B %d, %Y')
    except Exception:
        log.warning('Missing release date from TMDb')
        release = 'None'

    try:
        physical_release = datetime.strptime(
            radarr_data['physicalRelease'], '%Y-%m-%dT%H:%M:%SZ'
        ).strftime('%B %d, %Y')
    except Exception:
        log.warning('Missing physical release date from Radarr')
        physical_release = 'None'

    overview        = tmdb_movie.get('overview') or 'None'
    genres          = ', '.join(radarr_data.get('genres', [])) or 'None'
    quality_profile = get_quality_profile(cfg, radarr_data['qualityProfileId'])
    directors       = get_tmdb_directors(cfg, tmdb_movie_id)
    file_size       = human_size(radarr_data['sizeOnDisk'])

    poster_path = tmdb_movie.get('poster_path')
    poster_url  = f'https://image.tmdb.org/t/p/w500{poster_path}' if poster_path else 'https://i.imgur.com/GoqfZJe.jpg'

    imdb_url     = f'https://www.imdb.com/title/{imdb_id}'
    rt_url       = rt_url_for(media_title)
    ratings_text = (
        f'[<:imdb:688157397134606412> {imdb_rating}]({imdb_url}) '
        f'[{format_rt_score(rt_score)}]({rt_url})'
    )

    # Build Discord message
    message = {
        'username': cfg.radarr_discord_user,
        'content': f'New movie downloaded - {media_title} ({year}) IMDb: {imdb_rating}',
        'embeds': [
            {
                'author': {
                    'name': 'Movies',
                    'url': cfg.radarr_url,
                    'icon_url': cfg.radarr_icon,
                },
                'title': f'{media_title} ({year})',
                'color': 3394662,
                'url': f'{cfg.radarr_url}movie/{tmdb_movie_id}',
                'image': {'url': poster_url},
            },
            {
                'title': 'Overview',
                'color': 3381708,
                'description': overview,
                'fields': [
                    {'name': 'Quality',               'value': quality,           'inline': True},
                    {'name': 'Quality Profile',       'value': quality_profile,   'inline': True},
                    {'name': 'Release Date',          'value': release,           'inline': True},
                    {'name': 'Physical Release Date', 'value': physical_release,  'inline': True},
                    {'name': 'File Size',             'value': file_size,         'inline': True},
                    {'name': 'Ratings',               'value': ratings_text,      'inline': True},
                    {'name': 'Director',              'value': directors,         'inline': True},
                    {'name': 'Genres',                'value': genres,            'inline': True},
                    {'name': 'Trailer',               'value': trailer_link,      'inline': False},
                ],
                'footer': {'text': scene_name},
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        ],
    }

    # Send notification
    log.info(json.dumps(message, sort_keys=True, indent=4, separators=(',', ': ')))
    sender = requests.post(cfg.radarr_discord_url, headers=DISCORD_HEADERS, json=message)
    log.info(sender.text)
