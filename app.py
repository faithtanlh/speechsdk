<<<<<<< HEAD
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import azure.cognitiveservices.speech as speechsdk
import flask_cors as CORS

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS.CORS(app)

AZURE_SPEECH_KEY = ''
AZURE_SERVICE_REGION = 'southeastasia'

# Initialize configurations
speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SERVICE_REGION)

# Set the LanguageIdMode (Optional; Either Continuous or AtStart are accepted; Default AtStart)
speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, value='Continuous')

# Auto language detection configuration
auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-SG", "zh-CN", "ms-MY", "ta-IN", "zh-HK", "zh-TW"])

channels = 1
bits_per_sample = 16
samples_per_second = 16000

# Store recognizers and streams for each room
recognizers = {}
audio_streams = {}

def initialize_recognizer(room):
    wave_format = speechsdk.audio.AudioStreamFormat(samples_per_second, bits_per_sample, channels)
    audio_input_stream = speechsdk.audio.PushAudioInputStream(stream_format=wave_format)
    audio_config = speechsdk.audio.AudioConfig(stream=audio_input_stream)
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        auto_detect_source_language_config=auto_detect_source_language_config,
        audio_config=audio_config
    )
    
    speech_recognizer.recognized.connect(lambda evt: speech_recognizer_recognized_cb(evt, room))
    speech_recognizer.session_started.connect(speech_recognizer_session_started_cb)
    speech_recognizer.session_stopped.connect(speech_recognizer_session_stopped_cb)
    speech_recognizer.canceled.connect(speech_recognizer_recognition_canceled_cb)
    
    recognizers[room] = speech_recognizer
    audio_streams[room] = audio_input_stream

    return speech_recognizer, audio_input_stream

def speech_recognizer_recognition_canceled_cb(evt: speechsdk.SessionEventArgs):
    print('Canceled event')

def speech_recognizer_session_stopped_cb(evt: speechsdk.SessionEventArgs):
    print('SessionStopped event')

def speech_recognizer_recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs, room):
    print('TRANSCRIBED:')
    if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f'\tText={evt.result.text}')
        socketio.emit('transcription_result', {'text': evt.result.text, 'speakerId': 'Unknown'}, room=room)
    elif evt.result.reason == speechsdk.ResultReason.NoMatch:
        print('\tNOMATCH: Speech could not be TRANSCRIBED: {}'.format(evt.result.no_match_details))

def speech_recognizer_session_started_cb(evt: speechsdk.SessionEventArgs):
    print('SessionStarted event')

@app.route('/start_transcription', methods=['POST'])
def start_transcription():
    room = request.json.get("room")
    if room:
        speech_recognizer, audio_input_stream = initialize_recognizer(room)
        speech_recognizer.start_continuous_recognition_async()
        return {"message": "Transcription started"}, 200
    else:
        return {"error": "Room not specified"}, 400

@app.route('/stop_transcription', methods=['POST'])
def stop_transcription():
    room = request.json.get("room")
    if room:
        if room in recognizers:
            recognizers[room].stop_continuous_recognition_async()
            del recognizers[room]
            del audio_streams[room]
        return {"message": "Transcription stopped"}, 200
    else:
        return {"error": "Room not specified"}, 400

@socketio.on('audio_data')
def handle_audio_data(audio_data):
    room = request.sid
    print("Received audio data")
    if room in audio_streams:
        try:
            audio_streams[room].write(audio_data)
            print(f"Audio data length: {len(audio_data)}")
        except Exception as e:
            app.logger.error(f"Error handling audio data: {e}")
    else:
        app.logger.error("Audio stream for the room not found")

@socketio.on('connect')
def handle_connect():
    room = request.sid
    join_room(room)
    print(f'Client connected: {room}')
    emit('join_room', {'room': room})

@socketio.on('disconnect')
def handle_disconnect():
    room = request.sid
    leave_room(room)
    print(f'Client disconnected: {room}')
    if room in recognizers:
        recognizers[room].stop_continuous_recognition_async()
        del recognizers[room]
        del audio_streams[room]

if __name__ == '__main__':
    print("Starting server")
    socketio.run(app, host="0.0.0.0", port=8000)
=======
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
>>>>>>> e455908a42b591ae4558a063c9f30459a6263e3d
