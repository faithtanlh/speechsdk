import os
from flask import Flask, request
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit, join_room, leave_room
import azure.cognitiveservices.speech as speechsdk
import flask_cors as CORS

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS.CORS(app)
load_dotenv()

AZURE_SPEECH_KEY = os.getenv("SPEECHSDK_API_KEY")
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
    speech_recognizer.recognizing.connect(speech_recognizer_partial_cb)
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
        print('\tSpeaker ID={}'.format(evt.result.speaker_id))
        socketio.emit('transcription_result', {'text': evt.result.text, 'speakerId': evt.result.speaker_id}, room=room)
    elif evt.result.reason == speechsdk.ResultReason.NoMatch:
        print('\tNOMATCH: Speech could not be TRANSCRIBED: {}'.format(evt.result.no_match_details))

def speech_recognizer_partial_cb(evt):
    print(f"Partial result: {evt.result.text}")

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
def handle_audio_data(data):
    room = data["room"]
    audio_data = data["audio_data"]

    # print("Received audio data")
    if room in audio_streams:
        try:
            audio_streams[room].write(audio_data)
            # print(f"Audio data length: {len(audio_data)}")
        except Exception as e:
            app.logger.error(f"Error handling audio data: {e}")
    else:
        app.logger.error(f"Audio stream for the room not found: {room}")

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
    socketio.run(app, host="127.0.0.1", port=8000) # run locally
