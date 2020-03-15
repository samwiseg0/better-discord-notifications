# Scripts for better notifications from Sonarr and Radarr
Scripts that send better discord notifications from sonarr and radarr

## To install
1. `git clone https://github.com/samwiseg00/better-discord-notifications.git`

1. Download python dependencies `pip3 install -r requirements.txt`

1. Make a copy of `script_config.example.py` to `script_config.py`.

1. On sonarr/radarr add the script under, `settings > connect > Customscript` Run on download and on upgrade. Point to `radarr_discord.py` or `sonarr_discord.py`.

1. Docker folder has been added and includes local copies of the modules required. It should work inside sonarr v3 and radarr v3 containers. 

### Samples

<img height="600" alt="Example" src="https://i.imgur.com/mCB5lyi.png"> <img height="339" alt="Example" src="https://i.imgur.com/t6rWLWf.png">

Project is inspired by https://github.com/Dec64/Better_slack_notifcations
