import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

CORS(app, resources={r"/*": {"origins": "*"}})

api_key = "e5404bd89ea14c388c2c17234f95e36a"
region = "southeastasia"

speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
auto_detect_source_language_config = speechsdk.AutoDetectSourceLanguageConfig(languages=["en-US", "hi-IN"])
audio_config = speechsdk.AudioConfig(use_default_microphone=True)
speech_recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config,
    audio_config=audio_config,
    auto_detect_source_language_config=auto_detect_source_language_config
)

recognizing = False

def stop_recognition():
    global recognizing
    recognizing = False

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('start_transcription')
def handle_start_transcription():
    global recognizing
    if recognizing:
        return
    recognizing = True
    print("Transcription started")
    while recognizing:
        speech_recognition_result = speech_recognizer.recognize_once_async().get()
        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print(f"Recognized: {speech_recognition_result.text}")
            emit('transcription_result', speech_recognition_result.text)
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            emit('transcription_result', "No speech could be recognized")
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            emit('transcription_result', f"Speech Recognition canceled: {cancellation_details.reason}")

@socketio.on('stop_transcription')
def handle_stop_transcription():
    global recognizing
    if recognizing:
        print("Transcription stopped")
        stop_recognition()
        speech_recognizer.stop_continuous_recognition_async()
        # Additional logic to stop transcription if needed

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000)
