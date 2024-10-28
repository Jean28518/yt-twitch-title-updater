# yt-twitch-title-updater

Updates yt and twitch titles according to a timetable

## Deployment

```bash
cp config.json.example config.json

sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the script
python main.py
```

## Access YT API

<https://developers.google.com/youtube/v3/quickstart/python>

- You need to download the client_secret_*.json file and place it next to the config.json file.
