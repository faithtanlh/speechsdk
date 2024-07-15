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

CORS(app)

AZURE_SPEECH_KEY = ''
AZURE_SERVICE_REGION = ''

# Initialize configurations
speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SERVICE_REGION)

# Set the LanguageIdMode (Optional; Either Continuous or AtStart are accepted; Default AtStart)
speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, value='Continuous')

# Auto language detection configuration
auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-SG", "zh-CN", "ms-MY", "ta-IN", "zh-HK", "zh-TW"])

channels = 1
bits_per_sample = 16
samples_per_second = 16000

def initialize_recognizer():
    wave_format = speechsdk.audio.AudioStreamFormat(samples_per_second, bits_per_sample, channels)
    audio_input_stream = speechsdk.audio.PushAudioInputStream(stream_format=wave_format)
    audio_config = speechsdk.audio.AudioConfig(stream=audio_input_stream)
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        auto_detect_source_language_config=auto_detect_source_language_config,
        audio_config=audio_config
    )
    
    speech_recognizer.recognizing.connect(speech_recognizer_recognizing_cb)
    #speech_recognizer.recognized.connect(speech_recognizer_recognized_cb)
    speech_recognizer.session_started.connect(speech_recognizer_session_started_cb)
    speech_recognizer.session_stopped.connect(speech_recognizer_session_stopped_cb)
    speech_recognizer.canceled.connect(speech_recognizer_recognition_canceled_cb)
    
    return speech_recognizer, audio_input_stream

def speech_recognizer_recognition_canceled_cb(evt: speechsdk.SessionEventArgs):
    print('Canceled event')

def speech_recognizer_session_stopped_cb(evt: speechsdk.SessionEventArgs):
    print('SessionStopped event')

def speech_recognizer_recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
    print('TRANSCRIBED:')
    if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
       # detected_language_result = speechsdk.languageconfig.AutoDetectSourceLanguageResult(evt.result)
        #detected_language = detected_language_result.language
        print(f'\tText={evt.result.text}')
        #print(f'\tDetected Language={detected_language}')
        #socketio.emit('transcription_result', {'text': evt.result.text})
    elif evt.result.reason == speechsdk.ResultReason.NoMatch:
        print('\tNOMATCH: Speech could not be TRANSCRIBED: {}'.format(evt.result.no_match_details))

def speech_recognizer_recognizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
    print('RECOGNIZING:')
    if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
        print(f'\tText={evt.result.text}')
        socketio.emit('transcription_result', {'text': evt.result.text})

def speech_recognizer_session_started_cb(evt: speechsdk.SessionEventArgs):
    print('SessionStarted event')

transcribing_stop = False
speech_recognizer, audio_input_stream = initialize_recognizer()

@app.route('/start_transcription', methods=['POST'])
def start_transcription():
    global transcribing_stop, speech_recognizer, audio_input_stream
    transcribing_stop = False
    speech_recognizer.start_continuous_recognition_async()
    return {"message": "Transcription started"}, 200

@app.route('/stop_transcription', methods=['POST'])
def stop_transcription():
    global transcribing_stop, speech_recognizer, audio_input_stream
    transcribing_stop = True
    speech_recognizer.stop_continuous_recognition_async()
    # Reinitialize recognizer for the next session
    speech_recognizer, audio_input_stream = initialize_recognizer()
    return {"message": "Transcription stopped"}, 200

@socketio.on('audio_data')
def handle_audio_data(audio_data):
    global audio_input_stream
    print("Received audio data")
    if audio_data:
        try:
            audio_input_stream.write(audio_data)
            print(f"Audio data length: {len(audio_data)}")
        except Exception as e:
            app.logger.error(f"Error handling audio data: {e}")
    else:
        app.logger.error("Received empty audio data")

if __name__ == '__main__':
    print("Starting server")
    socketio.run(app, host="0.0.0.0", port=8000)
