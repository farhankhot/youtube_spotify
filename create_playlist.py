import json
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
import youtube_dl

from exceptions import ResponseException
from secrets import spotify_token

class CreatePlaylist:
    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}

    def get_youtube_client(self):
        """ Log Into Youtube, Copied from Youtube Data API """
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

        # if os.path.exists("CREDENTIALS_PICKLE_FILE"):
        #     with open("CREDENTIALS_PICKLE_FILE", 'rb') as f:
        #         credentials = pickle.load(f)
        # else:
        #     flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        #     credentials = flow.run_console()
        #     with open("CREDENTIALS_PICKLE_FILE", 'wb') as f:
        #         pickle.dump(credentials, f)

        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()

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
                # save all important info and skip any missing song and artist
                self.all_song_info[video_title] = {
                    "youtube_url": youtube_url,
                    "song_name": song_name,
                    "artist": artist,

                    # add the uri, easy to get song to put into playlist
                    "spotify_uri": self.get_spotify_uri(song_name, artist)

                }

    def create_playlist(self):

        user_id = input("Enter your spotify user id: ")
        # client_id = "a2bcb0c23d0c4d7d9432029823a2f74d"
        # # Get OAuth2 token to create a new spotify playlist
        # auth_query="https://accounts.spotify.com/authorize?client_id={}&redirect_uri=http:%2F%2Fexample.com%2Fcallback&scope=playlist-modify-public%20user-read-email&response_type=token&state=123".format(
        #     client_id
        # )
        # response_auth = requests.post(
        #     auth_query,
        #     # headers={
        #     #     "Content-Type": "application/x-www-form-urlencoded",
        #     #     "Authorization": "Basic {}".format(spotify_token)
        #     # }
        # )


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
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()

        # playlist id
        return response_json["id"]

    def get_spotify_uri(self, song_name, artist):
        """Search For the Song"""
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=50".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json['tracks']['items']

        # perhaps removing if would fix akon, abel bug
        # list index out of range
        if songs is not None:
            uri = songs[0]["uri"]
            return uri

    def add_song_to_playlist(self):
        """Add all liked songs into a new Spotify playlist"""
        # populate dictionary with our youtube playlist songs,
        # with spotify uris already stored in it
        self.get_playlist_videos()

        # collect all of uri
        # uris = [info["spotify_uri"]
        #         for song, info in self.all_song_info.items()]

        uris=[]
        for song, info in self.all_song_info.items():
            # print(info)
            uris.append(info["spotify_uri"])

        # create a new playlist
        playlist_id = self.create_playlist()

        # add all songs into new playlist
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)


        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        # check for valid response status
        if response.status_code != 200 or response.status_code != 201:
            raise ResponseException(response.status_code)

        response_json = response.json()
        return response_json


if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()
input("Press enter to exit")
