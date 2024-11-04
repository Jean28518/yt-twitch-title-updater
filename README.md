# yt-twitch-title-updater

Updates yt and twitch titles according to a timetable from ems

## Deployment

```bash
cp config.json.example config.json
# Edit the config.json file
vim config.json

sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the script
python main.py
```

## Access YT API

<https://developers.google.com/youtube/v3/quickstart/python>

- You need to download the client_secret_*.json file and place it next to the config.json file

## Access Twitch API

- Register a new application at <https://dev.twitch.tv/console/apps>
  - Set the OAuth Redirect URL to `http://localhost:17563`
- Title is only updated if the stream is live (because of the API limitations)
