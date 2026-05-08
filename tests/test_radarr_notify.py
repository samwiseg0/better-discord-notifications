import os
import sys
import pytest
from unittest.mock import patch, MagicMock

import radarr_notify


class MockCfg:
    radarr_url          = 'http://radarr.test/'
    radarr_key          = 'testkey'
    radarr_discord_user = 'TestBot'
    radarr_discord_url  = 'http://discord.test/webhook'
    radarr_icon         = 'http://icon.test/radarr.png'
    moviedb_key         = 'tmdbkey'
    radarr_imdbapi_key  = 'omdbkey'


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

class TestHumanSize:
    def test_bytes(self):
        assert radarr_notify.human_size(500) == '500 B'

    def test_kilobytes(self):
        assert radarr_notify.human_size(1500) == '1.5 KB'

    def test_megabytes(self):
        assert radarr_notify.human_size(1_500_000) == '1.5 MB'

    def test_gigabytes(self):
        assert radarr_notify.human_size(8_000_000_000) == '8 GB'

    def test_terabytes(self):
        assert radarr_notify.human_size(2_000_000_000_000) == '2 TB'


class TestRtUrlFor:
    def test_simple_title(self):
        assert radarr_notify.rt_url_for('Inception') == 'https://www.rottentomatoes.com/m/inception'

    def test_title_with_spaces(self):
        assert radarr_notify.rt_url_for('The Dark Knight') == 'https://www.rottentomatoes.com/m/the_dark_knight'

    def test_title_strips_special_chars(self):
        assert radarr_notify.rt_url_for("Schindler's List") == 'https://www.rottentomatoes.com/m/schindlers_list'


class TestFormatRtScore:
    def test_high_score_uses_fresh_tomato(self):
        result = radarr_notify.format_rt_score('85')
        assert '85%' in result
        assert 'tomato_whole' in result

    def test_low_score_uses_rotten_tomato(self):
        result = radarr_notify.format_rt_score('40')
        assert '40%' in result
        assert 'tomato_rot' in result

    def test_boundary_score_60_is_fresh(self):
        assert 'tomato_whole' in radarr_notify.format_rt_score('60')

    def test_boundary_score_59_is_rotten(self):
        assert 'tomato_rot' in radarr_notify.format_rt_score('59')

    def test_unknown_score(self):
        result = radarr_notify.format_rt_score('?')
        assert '?' in result
        assert 'tomato_rot' in result


# ---------------------------------------------------------------------------
# HTTP-dependent helpers
# ---------------------------------------------------------------------------

class TestGetQualityProfile:
    def test_returns_profile_name(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'name': 'Bluray-1080p'}
        with patch('radarr_notify.requests.get', return_value=mock_resp):
            assert radarr_notify.get_quality_profile(MockCfg, 1) == 'Bluray-1080p'

    def test_returns_unknown_on_error(self):
        with patch('radarr_notify.requests.get', side_effect=Exception('timeout')):
            assert radarr_notify.get_quality_profile(MockCfg, 1) == 'Unknown'


class TestGetImdbRating:
    def test_returns_rating_as_string(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'rating': {'aggregateRating': 8.5}}
        with patch('radarr_notify.requests.get', return_value=mock_resp):
            assert radarr_notify.get_imdb_rating('tt1234567') == '8.5'

    def test_returns_question_mark_on_error(self):
        with patch('radarr_notify.requests.get', side_effect=Exception('error')):
            assert radarr_notify.get_imdb_rating('tt1234567') == '?'


class TestGetRtScore:
    def test_returns_score_without_percent(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'Ratings': [
                {'Source': 'Internet Movie Database', 'Value': '8.5/10'},
                {'Source': 'Rotten Tomatoes', 'Value': '94%'},
            ]
        }
        with patch('radarr_notify.requests.get', return_value=mock_resp):
            assert radarr_notify.get_rt_score(MockCfg, 'tt1234567') == '94'

    def test_returns_question_mark_when_not_in_ratings(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'Ratings': []}
        with patch('radarr_notify.requests.get', return_value=mock_resp):
            assert radarr_notify.get_rt_score(MockCfg, 'tt1234567') == '?'

    def test_returns_question_mark_on_error(self):
        with patch('radarr_notify.requests.get', side_effect=Exception('error')):
            assert radarr_notify.get_rt_score(MockCfg, 'tt1234567') == '?'


class TestGetTmdbDirectors:
    def test_single_director(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'crew': [
                {'name': 'Christopher Nolan', 'job': 'Director'},
                {'name': 'John Doe',           'job': 'Producer'},
            ]
        }
        with patch('radarr_notify.requests.get', return_value=mock_resp):
            assert radarr_notify.get_tmdb_directors(MockCfg, 1234) == 'Christopher Nolan'

    def test_multiple_directors(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'crew': [
                {'name': 'Director A', 'job': 'Director'},
                {'name': 'Director B', 'job': 'Director'},
            ]
        }
        with patch('radarr_notify.requests.get', return_value=mock_resp):
            assert radarr_notify.get_tmdb_directors(MockCfg, 1234) == 'Director A, Director B'

    def test_returns_unknown_on_error(self):
        with patch('radarr_notify.requests.get', side_effect=Exception('error')):
            assert radarr_notify.get_tmdb_directors(MockCfg, 1234) == 'Unknown'


class TestGetLastDownload:
    HISTORY_RESPONSE = {
        'records': [{
            'movieId':     42,
            'sourceTitle': 'Inception.2010.BluRay.1080p',
            'quality':     {'quality': {'name': 'Bluray-1080p'}},
            'movie': {
                'title':  'Inception',
                'imdbId': 'tt1375666',
            },
        }]
    }

    def test_returns_parsed_fields(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = self.HISTORY_RESPONSE
        with patch('radarr_notify.requests.get', return_value=mock_resp):
            result = radarr_notify.get_last_download(MockCfg)

        assert result['movie_id']    == '42'
        assert result['media_title'] == 'Inception'
        assert result['imdb_id']     == 'tt1375666'
        assert result['quality']     == 'Bluray-1080p'
        assert result['scene_name']  == 'Inception.2010.BluRay.1080p'

    def test_falls_back_imdb_id_when_missing(self):
        record = {
            'records': [{
                'movieId':     1,
                'sourceTitle': 'Some.Movie',
                'quality':     {'quality': {'name': 'WEB-DL'}},
                'movie':       {'title': 'Some Movie'},
            }]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = record
        with patch('radarr_notify.requests.get', return_value=mock_resp):
            result = radarr_notify.get_last_download(MockCfg)

        assert result['imdb_id'] == 'tt1490017'


# ---------------------------------------------------------------------------
# run() — full notification flow
# ---------------------------------------------------------------------------

RADARR_ENV = {
    'radarr_eventtype':           'Download',
    'radarr_movie_id':            '42',
    'radarr_movie_title':         'Inception',
    'radarr_movie_imdbid':        'tt1375666',
    'radarr_moviefile_quality':   'Bluray-1080p',
    'radarr_moviefile_scenename': 'Inception.2010.BluRay.1080p',
}

RADARR_DATA = {
    'year':             2010,
    'youTubeTrailerId': 'abc123',
    'physicalRelease':  '2010-12-07T00:00:00Z',
    'genres':           ['Action', 'Sci-Fi'],
    'qualityProfileId': 1,
    'sizeOnDisk':       8_000_000_000,
}

TMDB_FIND_RESULT = {
    'movie_results': [{
        'id':           27205,
        'poster_path':  '/poster.jpg',
        'overview':     'A dream within a dream.',
        'release_date': '2010-07-16',
    }]
}


def _mock_get(url, **kwargs):
    m = MagicMock()
    m.raise_for_status = MagicMock()
    if 'api/v3/movie/' in url and 'qualityprofile' not in url:
        m.json.return_value = RADARR_DATA
    elif 'qualityprofile' in url:
        m.json.return_value = {'name': 'Bluray-1080p'}
    elif 'imdbapi.dev' in url:
        m.json.return_value = {'rating': {'aggregateRating': 8.8}}
    elif 'omdbapi.com' in url:
        m.json.return_value = {'Ratings': [{'Source': 'Rotten Tomatoes', 'Value': '87%'}]}
    elif 'themoviedb.org/3/find' in url:
        m.json.return_value = TMDB_FIND_RESULT
    elif 'themoviedb.org/3/movie' in url:
        m.json.return_value = {'crew': [{'name': 'Christopher Nolan', 'job': 'Director'}]}
    return m


class TestRun:
    def test_sends_notification_with_correct_title(self):
        with patch.dict(os.environ, RADARR_ENV), \
             patch('radarr_notify.requests.get', side_effect=_mock_get), \
             patch('radarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            radarr_notify.run(MockCfg)

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs['json']
        assert 'Inception' in payload['content']
        assert '2010' in payload['content']
        assert payload['username'] == 'TestBot'

    def test_test_mode_fetches_last_download(self):
        last_download = {
            'movie_id':    '99',
            'media_title': 'The Matrix',
            'imdb_id':     'tt0133093',
            'quality':     'Bluray-1080p',
            'scene_name':  'The.Matrix.1999.BluRay.1080p',
        }
        env = {**RADARR_ENV, 'radarr_eventtype': 'test'}
        with patch.dict(os.environ, env), \
             patch('radarr_notify.get_last_download', return_value=last_download), \
             patch('radarr_notify.requests.get', side_effect=_mock_get), \
             patch('radarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            radarr_notify.run(MockCfg)

        payload = mock_post.call_args.kwargs['json']
        assert 'The Matrix' in payload['content']

    def test_test_mode_exits_when_last_download_fails(self):
        env = {**RADARR_ENV, 'radarr_eventtype': 'test'}
        with patch.dict(os.environ, env), \
             patch('radarr_notify.get_last_download', side_effect=Exception('API error')):
            with pytest.raises(SystemExit):
                radarr_notify.run(MockCfg)

    def test_radarr_fetch_failure_exits(self):
        def fail_radarr(url, **kwargs):
            m = MagicMock()
            if 'api/v3/movie/' in url and 'qualityprofile' not in url:
                m.raise_for_status.side_effect = Exception('500')
            else:
                m.raise_for_status = MagicMock()
                m.json.return_value = _mock_get(url).json.return_value
            return m

        with patch.dict(os.environ, RADARR_ENV), \
             patch('radarr_notify.requests.get', side_effect=fail_radarr):
            with pytest.raises(SystemExit):
                radarr_notify.run(MockCfg)

    def test_missing_trailer_falls_back_to_none(self):
        def mock_get_no_trailer(url, **kwargs):
            m = _mock_get(url, **kwargs)
            if 'api/v3/movie/' in url and 'qualityprofile' not in url:
                data = RADARR_DATA.copy()
                data.pop('youTubeTrailerId', None)
                m.json.return_value = data
            return m

        with patch.dict(os.environ, RADARR_ENV), \
             patch('radarr_notify.requests.get', side_effect=mock_get_no_trailer), \
             patch('radarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            radarr_notify.run(MockCfg)

        fields = mock_post.call_args.kwargs['json']['embeds'][1]['fields']
        trailer = next(f for f in fields if f['name'] == 'Trailer')
        assert trailer['value'] == 'None'

    def test_missing_poster_uses_fallback_image(self):
        def mock_get_no_poster(url, **kwargs):
            m = _mock_get(url, **kwargs)
            if 'themoviedb.org/3/find' in url:
                m.json.return_value = {
                    'movie_results': [{
                        'id':           27205,
                        'poster_path':  None,
                        'overview':     'Overview.',
                        'release_date': '2010-07-16',
                    }]
                }
            return m

        with patch.dict(os.environ, RADARR_ENV), \
             patch('radarr_notify.requests.get', side_effect=mock_get_no_poster), \
             patch('radarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            radarr_notify.run(MockCfg)

        image_url = mock_post.call_args.kwargs['json']['embeds'][0]['image']['url']
        assert image_url == 'https://i.imgur.com/GoqfZJe.jpg'
