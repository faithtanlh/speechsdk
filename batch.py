import os
from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# Azure configuration
AZURE_SUBSCRIPTION_KEY = os.getenv('SPEECHSDK_API_KEY')  
AZURE_SPEECH_API_URL = "https://southeastasia.api.cognitive.microsoft.com/speechtotext/v3.2/transcriptions"


@app.route('/create-transcription', methods=['POST'])
def create_transcription():
    try:
        # Get JSON data from the request
        data = request.json
        
        if not data or 'contentUrls' not in data:
            return jsonify({'error': 'No contentUrls provided'}), 400

        # Prepare the payload as per your request
        payload = {
            "contentUrls": data['contentUrls'],
            "properties": {
                "diarizationEnabled": False,
                "wordLevelTimestampsEnabled": False,
                "punctuationMode": "DictatedAndAutomatic",
                "profanityFilterMode": "Masked"
            },
            "locale": "en-US",  # Use the default locale for your case
            "displayName": data.get("displayName", "Transcription of storage container using default model for en-US")
        }

        # Headers for the request
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_SUBSCRIPTION_KEY,
            "Content-Type": "application/json"
        }

        # Send POST request to Azure Speech-to-Text API
        response = requests.post(AZURE_SPEECH_API_URL, headers=headers, data=json.dumps(payload))
        
        # Check if the request was successful
        if response.status_code == 201:
            return jsonify({"message": "Transcription request accepted", "location": response.headers.get("Location")}), 201
        else:
            return jsonify({"error": "Failed to create transcription", "details": response.json()}), response.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)