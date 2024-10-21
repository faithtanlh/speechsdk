from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
import flask_cors as CORS
import os
import time
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS.CORS(app)

AZURE_SPEECH_KEY = os.environ.get('AZURE_SPEECH_KEY')
AZURE_SERVICE_REGION = os.environ.get('AZURE_SPEECH_REGION')

# Set up OpenAI API key and endpoint
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # Replace with your resource's URL

# Set up Azure OpenAI client
client = AzureOpenAI(
    api_version="2024-02-01", # Make sure to use the correct API version
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# Initialize configurations
speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SERVICE_REGION)

# Set the LanguageIdMode and diarization
speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, value='Continuous')
speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults, value='true')

# Auto language detection configuration
auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
    languages=["en-SG", "zh-CN", "ms-MY", "hi-IN"]
)

channels = 1
bits_per_sample = 16
samples_per_second = 16000

# Store recognizers and streams for each room
recognizers = {}
audio_streams = {}

def initialize_recognizer(room):
    audio_input_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=audio_input_stream)

    # Create conversation transcriber with diarization enabled
    conversation_transcriber = speechsdk.transcription.ConversationTranscriber(
        speech_config=speech_config,
        audio_config=audio_config,
        auto_detect_source_language_config=auto_detect_source_language_config
    )

    # Set up handlers for transcription
    conversation_transcriber.transcribed.connect(lambda evt: transcriber_handler(evt, room))
    conversation_transcriber.transcribing.connect(lambda evt: transcribing_handler(evt, room))

    conversation_transcriber.session_started.connect(session_started_handler)
    conversation_transcriber.session_stopped.connect(session_stopped_handler)

    recognizers[room] = conversation_transcriber
    audio_streams[room] = audio_input_stream

    return conversation_transcriber, audio_input_stream

def transcriber_handler(evt, room):
    if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
        speaker_id = evt.result.speaker_id if evt.result.speaker_id else 'Unknown Speaker'
        print(f"Final Transcription (Room: {room}) Speaker: {speaker_id}, Text: {evt.result.text}")

        # Collect transcriptions in the room's list
        room_transcriptions[room].append({'text': evt.result.text, 'timestamp': time.time()})

        socketio.emit('transcription_final_result', {'text': evt.result.text, 'speakerId': speaker_id}, room=room)

def transcribing_handler(evt, room):
    if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
        print(f"Partial Transcription (Room: {room}) Text: {evt.result.text}")
        socketio.emit('transcription_result', {'text': evt.result.text}, room=room)


def session_started_handler(evt: speechsdk.SessionEventArgs):
    print("Session started.")

def session_stopped_handler(evt: speechsdk.SessionEventArgs):
    print("Session stopped.")


# Function to generate chapter titles using Azure OpenAI
def generate_chapter_titles(text):
    # The prompt asks for chapter titles based on the provided transcript
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that generates concise chapter titles for transcripts. Your task is to analyze the text and create relevant titles based on context changes."

        },
        {
            "role": "user",
            "content": (
                f"Generate concise chapter titles for the following text:\n\n{text}. Each title should reflect a significant change in context. Pick out important titles at your discretion."
                "After generating the titles, update them into the full transcript, with every single word, at the appropriate locations. Only show the full transcript with titles."
                "Here is a sample transcript from a project meeting, the format should be something like this:\n\n"
                
                "1. Opening and Introductions\n"
                "Hi, everyone. Thanks for joining the meeting today. Let's go around and introduce ourselves quickly. I'm John, leading the project.\n\n"
                
                "2. Project Overview\n"
                "As you know, we're working on the new app update, so I just want to give a quick overview of where we are. The design phase is complete, and the dev team has started coding.\n\n"
                
                "3. Current Challenges\n"
                "We've hit a couple of issues with the backend integration. Sarah, could you update us on the server-side challenges?\n\n"
                
                "4. Team Member Updates\n"
                "Now let's hear from the rest of the team. Mark, can you give us an update on the frontend progress?\n\n"
                
                "5. Future Steps and Deadlines\n"
                "We need to finalize the testing timeline. Everyone should aim to complete their sections by the end of next week. Any blockers we should address?\n\n"
                
                "6. Closing Remarks\n"
                "Great, thanks for all the updates. Let's regroup next Friday and ensure we're on track for the final release. Have a great weekend!"
            )
        }

    ]

    # Request to the Azure OpenAI API using chat completions
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # Replace with your Azure GPT model deployment name
        messages=messages,
        #max_tokens=200,  # Limit tokens for a concise response
        temperature=0.7,  # Adjust to control creativity level
        n=1,  # Number of responses
    )

    # Extract and return the generated titles
    titles = completion.choices[0].message.content.strip()
    print("Titles:", titles)
    return titles

# Global dictionary to store transcriptions for each room
room_transcriptions = {}

# Function to periodically process transcriptions and generate chapter titles
def process_transcriptions_periodically(interval, transcriptions, room, processed_transcriptions=""):
    if transcriptions:
        # Combine all collected transcriptions
        new_transcriptions = ' '.join([entry['text'] for entry in transcriptions])
        
        # Combine newly collected transcriptions with previously processed ones
        combined_transcriptions = processed_transcriptions + ' ' + new_transcriptions
        
        print(f"Collected transcriptions for room {room}: {combined_transcriptions}")

        # Generate chapter titles based on the new additions
        chapter_titles = generate_chapter_titles(combined_transcriptions)
        print(f"Generated chapter titles for room {room}: {chapter_titles}")

        # Emit the chapter titles to the frontend
        socketio.emit('chapter_titles', {'titles': chapter_titles}, room=room)

        # Update processed transcriptions with the new additions
        processed_transcriptions += ' ' + new_transcriptions

    # Schedule the next processing
    threading.Timer(interval, process_transcriptions_periodically, [interval, transcriptions, room, processed_transcriptions]).start()


@app.route('/start_transcription', methods=['POST'])
def start_transcription():
    room = request.json.get("room")
    if room:
        # Initialize transcriptions list for this room if it doesn't exist
        if room not in room_transcriptions:
            room_transcriptions[room] = []

        conversation_transcriber, audio_input_stream = initialize_recognizer(room)
        conversation_transcriber.start_transcribing_async()

        # Start periodic transcription processing (every 15 seconds)
        process_transcriptions_periodically(15, room_transcriptions[room], room)

        return {"message": "Transcription started"}, 200
    else:
        return {"error": "Room not specified"}, 400

@app.route('/stop_transcription', methods=['POST'])
def stop_transcription():
    room = request.json.get("room")
    if room in recognizers:
        recognizers[room].stop_transcribing_async()
        del recognizers[room]
        del audio_streams[room]
        return {"message": "Transcription stopped"}, 200
    return {"error": "Room not specified"}, 400

@socketio.on('audio_data')
def handle_audio_data(audio_data):
    room = request.sid
    if room in audio_streams:
        try:
            audio_streams[room].write(audio_data)
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
    if room in recognizers:
        recognizers[room].stop_transcribing_async()
        del recognizers[room]
        del audio_streams[room]

if __name__ == '__main__':
    print("Starting server")
    socketio.run(app, host="0.0.0.0", port=8000)
