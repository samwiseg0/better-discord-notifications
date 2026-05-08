######## SET YOUR CONFIGURATION HERE ########
# Copy this file to script_config.py and fill in your values.
# script_config.py is gitignored so your credentials stay local.
#
# FourK inherits all Standard values — only override what differs
# (e.g. a separate 4K Radarr/Sonarr instance with its own URL/API key).

class Standard:
    ######## Sonarr ########
    sonarr_discord_user = 'User'
    sonarr_discord_url  = 'https://discordapp.com/api/webhooks/XXXXXXXXXXXXXXXX/XXXXXXXXXXXXXXXX'
    sonarr_url          = 'https://tv.domain.ltd/'
    sonarr_key          = 'XXXXXXXXXXXXXXXX'
    sonarr_icon         = 'https://raw.githubusercontent.com/Sonarr/Sonarr/develop/Logo/128.png'
    skyhook_url         = 'https://skyhook.sonarr.tv/v1/tvdb/shows/en/'  # no need to change

    ######## Radarr ########
    radarr_discord_user = 'User'
    radarr_discord_url  = 'https://discordapp.com/api/webhooks/XXXXXXXXXXXXXXXX/XXXXXXXXXXXXXXXX'
    radarr_url          = 'https://movies.domain.ltd/'
    radarr_key          = 'XXXXXXXXXXXXXXXX'
    radarr_icon         = 'https://raw.githubusercontent.com/Radarr/Radarr/develop/Logo/128.png'

    ######## External APIs ########
    moviedb_key        = 'XXXXXXXXXXXXXXXX'                 # themoviedb.org
    radarr_imdbapi_key = 'XXXXXXXXXXXX'                     # omdbapi.com — register at https://www.omdbapi.com/apikey.aspx


class FourK(Standard):
    sonarr_url = 'https://tv4k.domain.ltd/'
    sonarr_key = 'XXXXXXXXXXXXXXXX'
    radarr_url = 'https://movies4k.domain.ltd/'
    radarr_key = 'XXXXXXXXXXXXXXXX'
