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

@app.route("/get_workout", methods=["POST"])
def get_workout():
    data = request.get_json()
    muscle = data.get("muscle", "").lower()
    
    if not muscle:
        return jsonify({"error": "Please specify a muscle group."}), 400

    api_key = os.getenv("WORKOUT_API_KEY")
    url = f"https://api.api-ninjas.com/v1/exercises?muscle={muscle}"

    try:
        res = requests.get(url, headers={"X-Api-Key": api_key})
        res.raise_for_status()
        workouts = res.json()
        if not workouts:
            return jsonify({"error": "No exercises found for that muscle group."})
        
        # Limit to 5 workouts for display
        top_workouts = workouts[:5]
        return jsonify(top_workouts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_calories", methods=["POST"])
def get_calories():
    data = request.get_json()
    food_item = data.get("food", "").strip().lower()
    if not food_item:
        return jsonify({"error": "Please enter a food item."}), 400

    USDA_API_KEY = os.getenv("USDA_API_KEY")
    search_url = f"https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": USDA_API_KEY,
        "query": food_item,
        "pageSize": 1
    }

    try:
        search_response = requests.get(search_url, params=params)
        search_response.raise_for_status()
        search_data = search_response.json()

        if not search_data["foods"]:
            return jsonify({"error": "No data found for that food."})

        food = search_data["foods"][0]
        return jsonify({
            "name": food.get("description", "Unknown"),
            "calories": food.get("foodNutrients", [{}])[3].get("value", "N/A"),  # Approx index
            "protein": food.get("foodNutrients", [{}])[0].get("value", "N/A"),
            "carbohydrates": food.get("foodNutrients", [{}])[1].get("value", "N/A"),
            "fat": food.get("foodNutrients", [{}])[2].get("value", "N/A")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/top10", methods=["POST"])
def top10():
    data = request.get_json()
    category = data.get("category", "").strip()

    if not category:
        return jsonify({"error": "Please provide a category."}), 400

    try:
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        prompt = f"List the top 10 {category} of all time. Just give short names or labels for each item."

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-3.5-turbo",  # ← use 3.5 instead of gpt-4
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        top10_list = result["choices"][0]["message"]["content"]

        return jsonify({"top10": top10_list.strip()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/top_stocks", methods=["GET"])
def get_top_stocks():
    api_key = os.getenv("FINNHUB_API_KEY")
    url = "https://finnhub.io/api/v1/stock/symbol"
    params = {"exchange": "US", "token": api_key}

    try:
        symbols_res = requests.get(url, params=params)
        symbols = symbols_res.json()[:50]  # Limit for performane

        movers = []

        for stock in symbols:
            symbol = stock["symbol"]
            quote_url = "https://finnhub.io/api/v1/quote"
            quote_params = {"symbol": symbol, "token": api_key}
            quote_res = requests.get(quote_url, params=quote_params)

            if quote_res.status_code != 200:
                continue

            quote_data = quote_res.json()
            if quote_data["pc"] == 0:
                continue

            change_percent = ((quote_data["c"] - quote_data["pc"]) / quote_data["pc"]) * 100
            movers.append({
                "symbol": symbol,
                "change_percent": round(change_percent, 2)
            })
        movers.sort(key=lambda x: x["change_percent"], reverse=True)
        top_gainers = movers[:5]
        top_losers = movers[-5:][::-1]

        return jsonify({"gainers": top_gainers, "losers": top_losers})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/translate", methods=["POST"])
def translate_text():
    data = request.get_json()
    text = data.get("text", "")
    target = data.get("target", "en")

    GOOGLE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    url = "https://translation.googleapis.com/language/translate/v2"

    params = {
        "q": text,
        "target": target,
        "format": "text",
        "key": GOOGLE_API_KEY
    }

    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        translated = response.json()["data"]["translations"][0]["translatedText"]
        return jsonify({"translated_text": translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__": #calls main
    app.run(debug=True, host="0.0.0.0") #starts the flask server 
