from flask import Flask, render_template, request, jsonify 
import requests
import os
from dotenv import load_dotenv
import base64
import time
from google.cloud import texttospeech
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

#flask lets you create the app
#render_template loads html files like index.html
#request lets you access the data sent from the browser
#jsonify sends back a clean json response
#requests allows pythons to send HTTP requests 

app = Flask(__name__) # Create a Flask application instance , also tells flask this is the main file
spotify_token = None #access token for Spotify API
spotify_token_expiry = 0 #timestamp for when the Spotify token expires
API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn" #API endpoint for summarization model 
HEADERS = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_TOKEN')}"} # adds your API token to the request header (basicly saying Hey Hugging Face, Here's my API key)

@app.route("/") #when someone visits the root URL, this function will run
def home():
    return render_template("index.html") #load and return index file

@app.route("/summarize", methods=["POST"]) #this route runs when the brower sends a POST request to /summarize (user hits submit)
def summarize():
    input_text = request.form["text"] #gets the text that the user entered in the form on the website 
    word_count = len(input_text.split())
    if word_count < 300:
        return jsonify({"error": "Text must be at least 300 words for summarization."})
    
    payload = { # data that is sent to hugging face API
        "inputs": input_text,
        "options": {"wait_for_model": True} # makes sure the model is not asleep (aka lets it load)
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload) #sends the API request to Hugging Face
        response.raise_for_status() #checks is request was successful, if not it raises an error
        summary = response.json()[0]["summary_text"] # sets summary to the text returned by the API, which is in JSON format
        return jsonify({"summary": summary}) #returns the summary as a JSON response to the browser
    except Exception as e: #catches any errors
        return jsonify({"error": str(e)}) #return error to the browser as JSON

def get_spotify_token(): # Function to fetch Spotify API access token
    global spotify_token, spotify_token_expiry #lets function modify global variables

    if spotify_token and time.time() < spotify_token_expiry: # If token is still valid, return it
        return spotify_token

    client_id = os.getenv("SPOTIFY_CLIENT_ID") #gets client id from .env
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET") #gets client secret from .env
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode() #base64 is an encoder) combines client id and secret and encodes it has to do this for spotify

    response = requests.post( #sends a POSt to spotify
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    data = response.json() #parses the response
    spotify_token = data["access_token"] #store the token so we can reuse it
    spotify_token_expiry = time.time() + data["expires_in"] - 60 #calculates when token will expire (subtracts 60 seconds to be safe)
    return spotify_token #returns the token

@app.route("/get_song", methods=["POST"]) #defines rounte for get song
def get_song():
    user_input = request.form["vibe"] #gets the user input from the form on the website
    token = get_spotify_token() #gets a athorization token from Spotify

    headers = {"Authorization": f"Bearer {token}"} #adds the token to the header
    params = {"q": user_input, "type": "track", "limit": 1} #runs a query to search for a song based on user input only returns one

    r = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params) #sends a get request to Spotify API to search for a song
    data = r.json() #parses the response from Spotify API

    try:
        track = data["tracks"]["items"][0] #gets the first track from the response
        track_url = track["external_urls"]["spotify"] #gets url to the song
        track_name = track["name"] #gets the name of the song
        artist = track["artists"][0]["name"] #gets the name of the artist

        return jsonify({ #sends info back to the index.html file as json
            "url": track_url,
            "name": track_name,
            "artist": artist
        })
    except Exception as e: #catches any errors that occur if no song is found
        print("Error:", e)
        return jsonify({"error": "No results found."})

@app.route("/get_sports_highlights", methods=["POST"])
def get_sports_highlights():
    data = request.get_json()
    query = data.get("query", "")

    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Make sure this is in your .env

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query + " highlights",
        "type": "video",
        "maxResults": 5,
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch highlights"}), 500

    items = response.json().get("items", [])
    highlights = [
        {
            "title": item["snippet"]["title"],
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "videoUrl": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        }
        for item in items
    ]

    return jsonify(highlights)

@app.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    text = request.get_json().get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        audio_base64 = generate_audio(text)
        return jsonify({"audio": audio_base64})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def generate_audio(text: str) -> str:
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config
    )

    return base64.b64encode(response.audio_content).decode("utf-8")

@app.route("/get_places_by_city", methods=["POST"])
def get_places_by_city():
    data = request.get_json()
    city = data.get("city")
    keyword = data.get("keyword")

    GEOCODE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")  # Same key for both APIs

    # Step 1: Convert city name to coordinates
    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_params = {"address": city, "key": GEOCODE_API_KEY}
    geo_res = requests.get(geo_url, params=geo_params)
    geo_data = geo_res.json()

    if geo_data["status"] != "OK":
        return jsonify({"error": "City not found."}), 400

    location = geo_data["results"][0]["geometry"]["location"]
    lat_lng = f"{location['lat']},{location['lng']}"

    # Step 2: Search places near coordinates
    places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    places_params = {
        "location": lat_lng,
        "radius": 2000,
        "keyword": keyword,
        "key": GEOCODE_API_KEY
    }

    places_res = requests.get(places_url, params=places_params)
    places = places_res.json().get("results", [])

    results = [
        {
            "name": p["name"],
            "address": p.get("vicinity"),
            "rating": p.get("rating"),
            "location": p["geometry"]["location"]
        }
        for p in places
    ]

    return jsonify(results)

   
if __name__ == "__main__": #calls main
    app.run(debug=True, host="0.0.0.0") #starts the flask server 
