import os
import sys
import pytest
from unittest.mock import patch, MagicMock

import sonarr_notify


class MockCfg:
    sonarr_url          = 'http://sonarr.test/'
    sonarr_key          = 'testkey'
    sonarr_discord_user = 'TestBot'
    sonarr_discord_url  = 'http://discord.test/webhook'
    sonarr_icon         = 'http://icon.test/sonarr.png'
    skyhook_url         = 'https://skyhook.sonarr.tv/v1/tvdb/shows/en/'


# Skyhook response fixture. seasons is a list indexed by season number.
SKYHOOK_DATA = {
    'slug':          'breaking-bad',
    'overview':      'A chemistry teacher becomes a drug lord.',
    'contentRating': 'TV-MA',
    'network':       'AMC',
    'genres':        ['Drama', 'Crime'],
    'images': [
        {'url': 'http://img.test/series_banner.jpg'},
        {'url': 'http://img.test/series_banner2.jpg'},
    ],
    'seasons': [
        {},  # index 0 (unused / specials placeholder)
        {    # index 1 = Season 1
            'images': [
                {'url': 'http://img.test/s1_banner.jpg'},
                {'url': 'http://img.test/s1_banner2.jpg'},
            ]
        },
    ],
    'episodes': [
        {'seasonNumber': 1, 'episodeNumber': 1, 'overview': 'Walter White begins his transformation.'},
        {'seasonNumber': 1, 'episodeNumber': 2, 'overview': ''},
    ],
}

SONARR_ENV = {
    'sonarr_eventtype':                  'Download',
    'sonarr_episodefile_seasonnumber':   '1',
    'sonarr_episodefile_episodenumbers': '1',
    'sonarr_series_tvdbid':              '81189',
    'sonarr_episodefile_scenename':      'Breaking.Bad.S01E01.720p',
    'sonarr_series_title':               'Breaking Bad',
    'sonarr_episodefile_episodetitles':  'Pilot',
    'sonarr_episodefile_quality':        'HDTV-720p',
    'sonarr_isupgrade':                  'False',
}


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

class TestParseEpisodeNumbers:
    def test_single_episode(self):
        assert sonarr_notify.parse_episode_numbers('1') == [1]

    def test_multiple_episodes(self):
        assert sonarr_notify.parse_episode_numbers('1,2,3') == [1, 2, 3]

    def test_empty_string(self):
        assert sonarr_notify.parse_episode_numbers('') == []

    def test_non_numeric_string(self):
        assert sonarr_notify.parse_episode_numbers('abc') == []


class TestGetEpisodeOverview:
    EPISODES = [
        {'seasonNumber': 1, 'episodeNumber': 1, 'overview': 'Pilot overview'},
        {'seasonNumber': 1, 'episodeNumber': 2, 'overview': ''},
    ]

    def test_returns_episode_overview_when_found(self):
        result = sonarr_notify.get_episode_overview(self.EPISODES, 1, 1, 'fallback')
        assert result == 'Pilot overview'

    def test_empty_overview_falls_back(self):
        result = sonarr_notify.get_episode_overview(self.EPISODES, 1, 2, 'fallback')
        assert result == 'fallback'

    def test_missing_episode_falls_back(self):
        result = sonarr_notify.get_episode_overview(self.EPISODES, 2, 1, 'fallback')
        assert result == 'fallback'


class TestGetSeasonBanner:
    def test_returns_season_banner_when_found(self):
        url = sonarr_notify.get_season_banner(SKYHOOK_DATA, 1)
        assert url == 'http://img.test/s1_banner2.jpg'

    def test_falls_back_to_series_banner_for_missing_season(self):
        url = sonarr_notify.get_season_banner(SKYHOOK_DATA, 99)
        assert url == 'http://img.test/series_banner.jpg'


class TestGetLastDownload:
    HISTORY_RESPONSE = {
        'records': [{
            'sourceTitle': 'Breaking.Bad.S01E01.720p',
            'quality':     {'quality': {'name': 'HDTV-720p'}},
            'episode': {
                'seasonNumber':  1,
                'episodeNumber': 1,
                'title':         'Pilot',
            },
            'series': {
                'title':  'Breaking Bad',
                'tvdbId': 81189,
            },
        }]
    }

    def test_returns_parsed_fields(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = self.HISTORY_RESPONSE
        with patch('sonarr_notify.requests.get', return_value=mock_resp):
            result = sonarr_notify.get_last_download(MockCfg)

        assert result['season']        == '1'
        assert result['episode']       == '1'
        assert result['tvdb_id']       == '81189'
        assert result['media_title']   == 'Breaking Bad'
        assert result['episode_title'] == 'Pilot'
        assert result['quality']       == 'HDTV-720p'
        assert result['scene_name']    == 'Breaking.Bad.S01E01.720p'

    def test_missing_episode_title_defaults_to_empty(self):
        record = {
            'records': [{
                'sourceTitle': 'Show.S01E01',
                'quality':     {'quality': {'name': 'WEB-DL'}},
                'episode':     {'seasonNumber': 1, 'episodeNumber': 1},
                'series':      {'title': 'Show', 'tvdbId': 12345},
            }]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = record
        with patch('sonarr_notify.requests.get', return_value=mock_resp):
            result = sonarr_notify.get_last_download(MockCfg)

        assert result['episode_title'] == ''


# ---------------------------------------------------------------------------
# run() — full notification flow
# ---------------------------------------------------------------------------

def _mock_skyhook(url, **kwargs):
    m = MagicMock()
    m.json.return_value = SKYHOOK_DATA
    return m


class TestRun:
    def test_sends_notification_for_new_download(self):
        with patch.dict(os.environ, SONARR_ENV), \
             patch('sonarr_notify.requests.get', side_effect=_mock_skyhook), \
             patch('sonarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            sonarr_notify.run(MockCfg)

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs['json']
        assert 'Breaking Bad' in payload['content']
        assert 'Pilot' in payload['content']
        assert 'New episode' in payload['content']
        assert payload['username'] == 'TestBot'

    def test_upgrade_sets_correct_content_and_flag(self):
        env = {**SONARR_ENV, 'sonarr_isupgrade': 'True'}
        with patch.dict(os.environ, env), \
             patch('sonarr_notify.requests.get', side_effect=_mock_skyhook), \
             patch('sonarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            sonarr_notify.run(MockCfg)

        payload = mock_post.call_args.kwargs['json']
        assert 'Upgraded' in payload['content']
        fields = {f['name']: f['value'] for f in payload['embeds'][1]['fields']}
        assert fields['Upgrade?'] == 'Yes!'

    def test_episode_field_is_zero_padded(self):
        with patch.dict(os.environ, SONARR_ENV), \
             patch('sonarr_notify.requests.get', side_effect=_mock_skyhook), \
             patch('sonarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            sonarr_notify.run(MockCfg)

        fields = {f['name']: f['value'] for f in mock_post.call_args.kwargs['json']['embeds'][1]['fields']}
        assert fields['Episode'] == 's01e01'

    def test_test_mode_fetches_last_download(self):
        last_download = {
            'season':        '2',
            'episode':       '3',
            'tvdb_id':       '81189',
            'media_title':   'Breaking Bad',
            'episode_title': 'Bit by a Dead Bee',
            'quality':       'HDTV-720p',
            'scene_name':    'Breaking.Bad.S02E03.720p',
            'is_upgrade':    'False',
        }
        env = {**SONARR_ENV, 'sonarr_eventtype': 'test'}
        with patch.dict(os.environ, env), \
             patch('sonarr_notify.get_last_download', return_value=last_download), \
             patch('sonarr_notify.requests.get', side_effect=_mock_skyhook), \
             patch('sonarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            sonarr_notify.run(MockCfg)

        payload = mock_post.call_args.kwargs['json']
        assert 'Breaking Bad' in payload['content']

    def test_test_mode_exits_when_last_download_fails(self):
        env = {**SONARR_ENV, 'sonarr_eventtype': 'test'}
        with patch.dict(os.environ, env), \
             patch('sonarr_notify.get_last_download', side_effect=Exception('API error')):
            with pytest.raises(SystemExit):
                sonarr_notify.run(MockCfg)

    def test_skyhook_failure_exits(self):
        with patch.dict(os.environ, SONARR_ENV), \
             patch('sonarr_notify.requests.get', side_effect=Exception('network error')):
            with pytest.raises(SystemExit):
                sonarr_notify.run(MockCfg)

    def test_metadata_fields_are_populated(self):
        with patch.dict(os.environ, SONARR_ENV), \
             patch('sonarr_notify.requests.get', side_effect=_mock_skyhook), \
             patch('sonarr_notify.requests.post') as mock_post:
            mock_post.return_value.text = 'ok'
            sonarr_notify.run(MockCfg)

        fields = {f['name']: f['value'] for f in mock_post.call_args.kwargs['json']['embeds'][1]['fields']}
        assert fields['Content Rating'] == 'TV-MA'
        assert fields['Network'] == 'AMC'
        assert fields['Genres'] == 'Drama, Crime'
