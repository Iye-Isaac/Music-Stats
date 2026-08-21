import os

import secrets

# simple in-memory store: token -> spotify token_info
# NOTE: resets on every Render restart/redeploy, and only works if
# WEB_CONCURRENCY=1 (Render already defaults to this on free tier)
user_tokens = {}

FRAMER_STATS_URL = "https://mymix.framer.website/stats" 

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
    return redirect('https://mymix.framer.website/stats')


@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    token_info = cache_handler.get_cached_token()

    user_token = secrets.token_urlsafe(16)
    user_tokens[user_token] = token_info

    return redirect(f"{FRAMER_STATS_URL}?token={user_token}")


from spotipy.cache_handler import MemoryCacheHandler

@app.route('/user_top_read')
def user_top_read():
    token = request.args.get('token')
    token_info = user_tokens.get(token)

    if not token_info:
        return jsonify({'error': 'invalid or missing token'}), 401

    memory_cache = MemoryCacheHandler(token_info=token_info)
    oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_handler=memory_cache
    )
    sp = Spotify(auth_manager=oauth)

    top_artists = sp.current_user_top_artists(limit=10, time_range='medium_term')
    top_artists_ = [
        (artist['name'], artist['external_urls']['spotify'], artist['images'][0]['url'] if artist['images'] else None)
        for artist in top_artists['items']
    ]

    top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')
    top_tracks_ = [
        (track['name'], track['external_urls']['spotify'], track['album']['images'][0]['url'] if track['album']['images'] else None)
        for track in top_tracks['items']
    ]

    # save back in case spotipy refreshed the access token during this call
    user_tokens[token] = memory_cache.get_cached_token()

    return jsonify({
        'top_artists': [{'name': n, 'url': u, 'image': img} for n, u, img in top_artists_],
        'top_tracks': [{'name': n, 'url': u, 'image': img} for n, u, img in top_tracks_]
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)