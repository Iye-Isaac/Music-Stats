import os

from dotenv import load_dotenv

from flask import Flask, session, url_for, redirect, request, jsonify

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # add this right after creating the app


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)

client_id = os.environ.get('SPOTIFY_CLIENT_ID')
client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI')
scope = "user-top-read"



cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)

sp = Spotify(auth_manager=sp_oauth)

@app.route('/')
def home():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for('user_top_read'))


@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('user_top_read'))


@app.route('/user_top_read')
def user_top_read():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)

    top_artists = sp.current_user_top_artists(limit=10, time_range='medium_term')
    top_artists_ = [(artist['name'], artist['external_urls']['spotify']) for artist in top_artists['items']]

    top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')
    top_tracks_ = [(track['name'], track['external_urls']['spotify']) for track in top_tracks['items']]

    return jsonify({
        'top_artists': [{'name': n, 'url': u} for n, u in top_artists_],
        'top_tracks': [{'name': n, 'url': u} for n, u in top_tracks_]
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)