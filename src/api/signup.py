import threading
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import mysql.connector
from dotenv import load_dotenv
import os
import time
from fastapi import FastAPI
import uvicorn

app = FastAPI()

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = 'https://runner.up.railway.app/callback'
DB_HOST = os.getenv("MYSQLHOST")
DB_USER = os.getenv("MYSQLUSER")
DB_PASSWORD = os.getenv("MYSQLPASSWORD")
DB_NAME = os.getenv("MYSQLDATABASE")
DB_PORT = os.getenv("MYSQLPORT")


# Connect to the database
db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    port=DB_PORT,
    database=DB_NAME
)

# Create the database if it doesn't exist
cursor = db.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(DB_NAME))
db.database = DB_NAME

# Create the songs table if it doesn't exist
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS songs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        track_name VARCHAR(255),
        artist_name VARCHAR(255),
        played_at DATETIME
    )
    """
)
cursor.close()
db.close()

# Connect to the database with the specified database name
db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)

# Create a Spotify client with authorization
scope = 'user-read-playback-state'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope=scope))

# Track the last known playback state
last_playback_state = None


# Store the song data in the database
def store_song_data(track):
    cursor = db.cursor()
    sql = "INSERT INTO songs (track_name, artist_name, played_at) VALUES (%s, %s, %s)"
    values = (track['name'], track['artists'][0]['name'], track['played_at'])
    cursor.execute(sql, values)
    db.commit()
    cursor.close()


# Subscribe to playback updates
def subscribe_to_playback_updates():
    while True:
        current_playback_state = sp.current_user_playing_track()
        if current_playback_state is not None and current_playback_state != last_playback_state:
            store_song_data(current_playback_state['item'])
            last_playback_state = current_playback_state
        time.sleep(60)  # Wait for 1 minute before checking again


# Define a route for the root endpoint
@app.get("/")
def root():
    return {"message": "Hello, World!"}


# Define a route for handling Spotify callback
@app.get("/callback")
def spotify_callback(code: str):
    sp.auth_manager.get_access_token(code)
    return {"message": "Authorization successful"}


if __name__ == '__main__':
    # Run the playback update subscription in a background thread
    t = threading.Thread(target=subscribe_to_playback_updates)
    t.start()

    # Run the FastAPI application
    uvicorn.run(app, host='0.0.0.0', port=8000)


