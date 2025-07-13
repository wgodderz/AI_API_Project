from flask import Flask, render_template, request, jsonify 
import requests
import os
#flask lets you create the app
#render_template loads html files like index.html
#request lets you access the data sent from the browser
#jsonify sends back a clean json response
#requests allows pythons to send HTTP requests 

app = Flask(__name__) # Create a Flask application instance , also tells flask this is the main file

API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn" #API endpoint for summarization model 
Headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_TOKEN')}"} # adds your API token to the request header (basicly saying Hey Hugging Face, Here's my API key)

@app.route("/") #when someone visits the root URL, this function will run
def home():
    return render_template("index.html") #load and return index file

@app.route("/summarize", methods=["POST"]) #this route runs when the brower sends a POST request to /summarize (user hits submit)
def summarize():
    input_text = request.form["text"] #gets the text that the user entered in the form on the website 

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

if __name__ == "__main__": #calls main
    app.run(debug=True, host="0.0.0.0") #starts the flask server 
