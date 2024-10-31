import os
import json
import requests
from datetime import datetime
from datetime import timedelta
import time

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from twitchAPI.helper import first


import asyncio



SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def main():
    # Authenticate with the YouTube API
    authenticate()

    while True:
        sync_video_titles()
        time.sleep(60)


def sync_video_titles():
    # for every room in the config, get the current event and update the video title if necessary
    config = get_config()
    for room_assignment in config["room-assignments"]:
        room_id = room_assignment["ems-room-id"]
        video_id = room_assignment["yt-video-id"]
        room_name = room_assignment["room-name"]
        twitch_streamer_name = room_assignment["twitch-streamer-name"]
        lecture = get_current_ems_lecture_for_room(room_id)
        wanted_title = ""
        if lecture:
            wanted_title = f"{config['event-name']}: {lecture['title']} ({room_name})"
        else:
            wanted_title = f"{config['event-name']} ({room_name})"

        if not video_id.strip() == "":
            current_title = get_video_snippet_by_id(video_id)["title"]
            if current_title != wanted_title:
                update_video_title(video_id, wanted_title)
        
        if not twitch_streamer_name.strip() == "":
            streamer_id = asyncio.run(get_twitch_streamer_id(twitch_streamer_name))
            # We can only update the title if the stream is live because of twitch
            if asyncio.run(is_twitch_stream_live(streamer_id)):
                current_title = asyncio.run(get_twitch_stream_title(streamer_id))
                if current_title != wanted_title:
                    asyncio.run(update_twitch_stream_title(streamer_id, wanted_title))
        



def get_config():
    config = json.load(open("config.json", "r"))
    return config


def get_current_ems_lecture_for_room(room_id: int) -> dict:
    config = get_config()
    event_id = config["ems-event-id"]
    lectures = get_ems_timetable(event_id)
    now = datetime.now()
    # The format of lecture scheduled_presentation_time is 2024-11-02T09:00:00
    for lecture in lectures:
        if lecture["scheduled_in_room_id"] != room_id:
            continue
        start_time = datetime.strptime(lecture["scheduled_presentation_time"], "%Y-%m-%dT%H:%M:%S")
        # duration is in minutes
        scheduled_duration = lecture["scheduled_presentation_length"]
        end_time = start_time + timedelta(minutes=scheduled_duration)
        if start_time <= now <= end_time:
            return lecture

    
def get_ems_timetable(event_id) -> list:
    config = get_config()
    # Get the event data from the EMS API
    if config["ems-url"].endswith("/"):
        config["ems-url"] = config["ems-url"][:-1]
    ems_url = f"{config['ems-url']}/events/api/{event_id}/"
    response = requests.get(ems_url)
    event_data = response.json()
    return event_data["lectures"]


def authenticate():
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"

    # Get the client_secret filename:
    client_secrets_file = ""
    for file in os.listdir():
        if file.endswith(".json") and "client_secret" in file:
            client_secrets_file = file
            break

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
               client_secrets_file, SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=creds)

    return youtube
    

def get_video_snippet_by_id(video_id):
    youtube = authenticate()
    request = youtube.videos().list(
        part="snippet",
        id=video_id
    )
    response = request.execute()
    return response["items"][0]["snippet"]


def update_video_title(video_id, new_title):
    print(f"Updating video title for video with ID {video_id} to {new_title}")

    video_snippet = get_video_snippet_by_id(video_id)
    # print(response)

    # Update the title of the video
    video_snippet["title"] = new_title

    youtube = authenticate()

    # Update the video with the new snippet
    request = youtube.videos().update(
        part="snippet",
        body={
            "id": video_id,
            "snippet": video_snippet
        }
    )
    response = request.execute()
    # print(response)

async def get_twitch():
    config = get_config()
    client_id = config["twitch-client-id"]
    client_secret = config["twitch-client-secret"]

    # Load the auth token from the file token_twitch.json if it exists
    if os.path.exists("token_twitch.json"):
        with open("token_twitch.json", "r") as token_file:
            old_tokens = json.load(token_file)
    
    # Try to authenticate with the Twitch API with the old tokens
    try:
        twitch = await Twitch(client_id, client_secret)
        await twitch.set_user_authentication(old_tokens["token"], [AuthScope.CHANNEL_MANAGE_BROADCAST, AuthScope.USER_EDIT], old_tokens["refresh_token"])
        return twitch
    except:
        pass
            

    twitch = await Twitch(client_id, client_secret)

    target_scope = [AuthScope.CHANNEL_MANAGE_BROADCAST, AuthScope.USER_EDIT]
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)
    # this will open your default browser and prompt you with the twitch verification website
    token, refresh_token = await auth.authenticate()

    # Save the new tokens to the file token_twitch.json
    with open("token_twitch.json", "w") as token_file:
        json.dump({"token": token, "refresh_token": refresh_token}, token_file)

    await twitch.set_app_authentication(token, [AuthScope.CHANNEL_MANAGE_BROADCAST, AuthScope.USER_EDIT])

    return twitch

async def get_twitch_streamer_id(streamer_name):
    twitch = await get_twitch()
    twitch_user = await first(twitch.get_users(logins=[streamer_name]))
    return twitch_user.id
    
    
   

async def get_twitch_stream_title(streamer_id):
    twitch = await get_twitch()
    # stream_metadata = await first(twitch.get_streams(user_login=[streamer_name], stream_type="all", first=1))
    channel_information = (await twitch.get_channel_information(streamer_id))[0]
    return channel_information.title
   
async def is_twitch_stream_live(streamer_id):
    twitch = await get_twitch()
    stream = await first(twitch.get_streams(user_id=streamer_id))
    return stream is not None

async def update_twitch_stream_title(streamer_id, new_title):
    print(f"Updating Twitch stream title for streamer with ID {streamer_id} to {new_title}")
    twitch = await get_twitch()
    await twitch.modify_channel_information(streamer_id, title=new_title)

async def get_twitch_stream_key(streamer_id):
    twitch = await get_twitch()
    stream_key = await twitch.get_stream_key(streamer_id)
    return stream_key
   


if __name__ == "__main__":
    main()

