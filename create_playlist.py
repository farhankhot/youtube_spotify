import json
import os
import random
import pickle
import string
import base64

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
import youtube_dl
import spotipy
import spotipy.util as util

from spotipy import oauth2
from exceptions import ResponseException
# from secrets import spotify_token


class CreatePlaylist:
    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}
        self.spotify_token = self.auth_spotify_account()

    def get_youtube_client(self):
        """ Log Into Youtube, Copied from Youtube Data API """
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "C:/Users/Farhan Khot/youtube_spotify/youtube_spotify/client_secret.json"
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

        # This change from original code makes it so that I dont have to authenticate each time with google
        if os.path.exists("CREDENTIALS_PICKLE_FILE"):
            with open("CREDENTIALS_PICKLE_FILE", 'rb') as f:
                credentials = pickle.load(f)
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            credentials = flow.run_console()
            with open("CREDENTIALS_PICKLE_FILE", 'wb') as f:
                pickle.dump(credentials, f)

        # Get credentials and create an API client
        # flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        #     client_secrets_file, scopes)
        # credentials = flow.run_console()

        # from the Youtube DATA API
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube_client

    def get_playlist_videos(self):
        val = input("Enter your youtube playlist id: ")

        # Grab our playlists
        request = self.youtube_client.playlistItems().list(
            maxResults=50,
            part="snippet,contentDetails",
            playlistId=val
        )

        response = request.execute()

        # collect each video and get important information
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(
                item["contentDetails"]["videoId"])
            # use youtube_dl to collect the song name & artist name
            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            song_name = video["track"]
            artist = video["artist"]

            if song_name is not None and artist is not None:
                # artist = artist.replace("Various Artists", "")
                # Song preproccessing
                song_name = song_name.replace('Album', '')
                song_name = song_name.replace('Official', '')
                song_name = song_name.replace('Video', '')
                song_name = song_name.replace('Audio', '')
                song_name = song_name.replace('Lyrics','')
                song_name = song_name.replace('Version','')
                song_name = song_name.replace('Super Clean', '')
                song_name = song_name.replace('Instrumental', '')
                song_name = song_name.replace('.', '')
                # Can't feel my face bug
                song_name = song_name.replace("'", "")
                if artist == "Various Artists":
                    continue
                else:
                    # save all important info and skip any missing song and artist
                    self.all_song_info[video_title] = {
                        "youtube_url": youtube_url,
                        "song_name": song_name,
                        "artist": artist,

                        # add the uri, easy to get song to put into playlist
                        "spotify_uri": self.get_spotify_uri(song_name, artist)

                    }
                # print(self.all_song_info)

    def auth_spotify_account(self):
        user_name = input("Enter spotify username: ")
        client_id = "a2bcb0c23d0c4d7d9432029823a2f74d"
        client_secret = "7586151c22194f568d42b598614ce6a3"
        redirect_uri = "http://localhost:8000/"

        token = util.prompt_for_user_token(user_name, client_id = client_id, client_secret = client_secret,
        redirect_uri = redirect_uri, scope = "user-read-email user-read-private playlist-modify-public")
        sp = spotipy.Spotify(auth = token)
        print(sp.user(user_name))
        # print(token)
        return token

    def create_playlist(self):
        user_id = input("Enter your spotify user id: ")

        """Create A New Playlist"""
        request_body = json.dumps({
            "name": "AutomateAton",
            "description": "AutomateAton (youtube_spotify)",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(
            user_id)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        response_json = response.json()
        # print(response_json)

        # playlist id
        return response_json["id"]

    def get_spotify_uri(self, song_name, artist):

        # Song name preproccessing
        song_name = song_name.replace('album', '')
        song_name = song_name.replace('official', '')
        song_name = song_name.replace('video', '')
        song_name = song_name.replace('audio', '')
        song_name = song_name.replace('lyrics','')
        song_name = song_name.replace('version','')
        song_name = song_name.replace('super clean', '')
        song_name = song_name.replace('$','s')
        # song_name = song_name.replace('x','')

        """Search For the Song"""
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )

        response_json = response.json()
        song = response_json['tracks']['items']

        uri=""
        if song:
            uri = song[0]["uri"]
            return uri
        else:
            print("not on spotify")

    def add_song_to_playlist(self):
        # Populate dictionary with our youtube playlist songs,
        # with spotify uris already stored in it
        self.get_playlist_videos()

        # Collect all of uri (different syntax, same thing)
        # uris = [info["spotify_uri"]
        #         for song, info in self.all_song_info.items()]

        uris=[]
        for song, info in self.all_song_info.items():
            # print(info)
            if info["spotify_uri"]:
                uris.append(info["spotify_uri"])

        # for _ in uris:
        #     print("uri: %s" % _)

        # Create a new playlist
        playlist_id = self.create_playlist()

        # Add all songs into new playlist
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )

        # check for valid response status
        if response.status_code != 201:
            raise ResponseException(response.status_code)

        response_json = response.json()
        return response_json


if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()
