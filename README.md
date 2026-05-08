# Better Discord Notifications for Sonarr and Radarr

Scripts that send richer Discord notifications from Sonarr and Radarr, including IMDb/Rotten Tomatoes ratings, TMDb poster art, director credits, file size, and more.

## Install

### Standard (non-Docker)

1. Clone the repo:

   ```sh
   git clone https://github.com/samwiseg00/better-discord-notifications.git
   cd better-discord-notifications
   ```

2. Create and activate a virtual environment:

   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

4. Copy the example config and fill in your values:

   ```sh
   cp script_config.example.py script_config.py
   ```

5. In Sonarr/Radarr go to **Settings → Connect → Custom Script**, enable _On File Import_ and _On File Upgrade_, and point to the full path of the appropriate script:
   - `sonarr_discord.py` — standard Sonarr instance
   - `radarr_discord.py` — standard Radarr instance
   - `sonarr_discord_4k.py` — 4K Sonarr instance
   - `radarr_discord_4k.py` — 4K Radarr instance

### Docker

Use the scripts inside the `docker/` folder instead. This folder contains vendored copies of all required modules so the scripts can run inside Sonarr/Radarr containers where `pip install` is not available.

1. Copy the example config into the `docker/` folder:

   ```sh
   cp script_config.example.py docker/script_config.py
   ```

2. Edit `docker/script_config.py` with your values — this file must be modified by the user before the scripts will work.

3. Point Sonarr/Radarr to the corresponding script inside `docker/`.

## Configuration

`script_config.py` uses two classes:

- **`Standard`** — your main Sonarr/Radarr instance
- **`FourK`** — inherits everything from `Standard`; only override the fields that differ for your 4K instance (URL, API key)

See [`script_config.example.py`](script_config.example.py) for all available options.

### External API keys required

| API                                             | Used for                             | Cost |
| ----------------------------------------------- | ------------------------------------ | ---- |
| [TMDb](https://www.themoviedb.org/settings/api) | Poster art, release dates, directors | Free |
| [OMDb](https://www.omdbapi.com/apikey.aspx)     | Rotten Tomatoes score                | Free |

## Test Mode

Clicking **Test** in Sonarr/Radarr's Connect settings triggers the script with `eventtype=test`. Rather than sending a notification with dummy placeholder data, the script queries the Sonarr/Radarr history API and sends a real notification using the most recently downloaded item. This means the test result looks identical to a live notification.

## Development & Testing

Install dev dependencies (includes pytest):

```sh
pip install -r requirements-dev.txt
```

Run the test suite:

```sh
pytest tests/ -v
```

Run with coverage:

```sh
pytest tests/ -v --cov=. --cov-report=term-missing
```

## Samples

<img height="600" alt="Example" src="https://i.imgur.com/mCB5lyi.png"> <img height="339" alt="Example" src="https://i.imgur.com/t6rWLWf.png">

---

Inspired by [Dec64/Better\_slack\_notifications](https://github.com/Dec64/Better_slack_notifcations)
