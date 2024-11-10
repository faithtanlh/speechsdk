from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
import flask_cors as CORS
import os
import time
import threading
import pandas as pd

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS.CORS(app)

AZURE_SPEECH_KEY = os.environ.get('AZURE_SPEECH_KEY')
AZURE_SERVICE_REGION = os.environ.get('AZURE_SPEECH_REGION')

# Set up OpenAI API key and endpoint
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # Replace with your resource's URL

# Set up Azure Text Analytics key and endpoint
TEXT_ANALYTICS_KEY = os.getenv('TEXT_ANALYTICS_KEY')
TEXT_ANALYTICS_ENDPOINT = os.getenv('TEXT_ANALYTICS_ENDPOINT')

# Set up Azure OpenAI client
client = AzureOpenAI(
    api_version="2024-02-01", # Make sure to use the correct API version
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# Set up Azure Text Analytics client
text_analytics_client = TextAnalyticsClient(
    endpoint=TEXT_ANALYTICS_ENDPOINT,
    credential=AzureKeyCredential(TEXT_ANALYTICS_KEY),
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

# Function to generate SOAP summary using Azure OpenAI
def generate_soap_summary(text):
    # The prompt asks for a SOAP summary based on the provided transcript
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that generates SOAP (Subjective, Objective, Assessment, Plan) summaries for doctor-patient consultations. Your task is to analyze the text and create a structured summary in the SOAP format."
        },
        {
            "role": "user",
            "content": (
                f"Generate a concise SOAP summary for the following doctor-patient consultation:\n\n{text}."
                "Organize the summary according to the SOAP format, with each section as follows:\n\n"
                "1. Subjective:\n"
                "Capture the patient’s self-reported symptoms, history, and any other relevant subjective details shared by the patient.\n"
                
                "2. Objective:\n"
                "Include the clinician’s observations, examination findings, and any measurable or observable data.\n"
                
                "3. Assessment:\n"
                "Summarize the clinician’s diagnosis or assessment of the patient’s condition based on the consultation.\n"
                
                "4. Plan:\n"
                "Outline the treatment plan, including any prescribed medications, recommended follow-up actions, or further tests.\n\n"
                
                "If any section lacks sufficient information, please state 'Insufficient information provided' for that section.\n\n"

                "Here is an example of a SOAP summary:\n\n"
                
                "1. Subjective:\n"
                "Patient reports persistent headaches for the past two weeks, with throbbing pain around the temples. Pain is moderate but worsening during stress, with no other symptoms such as nausea.\n\n"
                
                "2. Objective:\n"
                "Vital signs normal. Neurological exam reveals no abnormalities; reflexes and coordination are intact. No signs of infection in ears, throat, or sinuses.\n\n"
                
                "3. Assessment:\n"
                "Likely diagnosis is tension headaches, potentially stress-induced. Family history suggests possible migraines but currently less likely.\n\n"
                
                "4. Plan:\n"
                "Recommend tracking headache patterns and using NSAIDs as needed. Referral to neurologist for further evaluation if migraines persist. Follow-up in two weeks.\n\n"
                
                "Please return the SOAP summary with these four sections clearly labeled."
            )
        }
    ]

    # Request to the Azure OpenAI API using chat completions
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # Replace with your Azure GPT model deployment name
        messages=messages,
        # max_tokens=200,  # Limit tokens for a concise response
        temperature=0.7,  # Adjust to control creativity level
        n=1,  # Number of responses
    )

    # Extract and return the generated SOAP summary
    soap_summary = completion.choices[0].message.content.strip()
    print("SOAP Summary:", soap_summary)
    return soap_summary


# Function to achieve HER for checkbox ticking
flags = { 'SymptomOrSign': False, 'Diagnosis': False, 'BodyStructure': False, 'Time': False, 'TreatmentName': False }
triggered_entities = []

def generate_checkbox_flags(text):
    words_to_remove = {'ok', 'yeah', 'yea', 'ya', 'hello', 'hi', 'bye', 'oh'}
    print(f"Processing chunk:\n{text}")

    # hypothesis_text_list = [sent.strip() for sent in text.lower().split('. ') if sent.strip()]
    hypothesis_text_list = [sent.strip() for sent in text.lower().split('. ') 
                            if sent.strip().lower() not in words_to_remove]
    long_sentences = " ".join([sent for sent in hypothesis_text_list if len(sent.split()) > 10])

    poller = text_analytics_client.begin_analyze_healthcare_entities([long_sentences])
    result = poller.result()
    docs = [doc for doc in result if not doc.is_error]

    # Extract and create DataFrame in one step
    entities_data = [(entity.category, entity.confidence_score, entity.text) 
                        for doc in docs for entity in doc.entities if entity.category]
    her_df = pd.DataFrame(entities_data, columns=['category', 'confidence_score', 'text'])

    # Set flags based on entity categories and confidence scores and store triggering entities
    for category in flags.keys():
        if not flags[category]:  # Only check if flag is not already set
            matches = her_df.loc[(her_df['category'] == category) & 
                                    (her_df['confidence_score'] >= 0.89)]
            if not matches.empty:
                flags[category] = True
                # Save triggering entities to tracking list
                triggered_entities.extend(matches[['category', 'confidence_score', 'text']].to_dict('records'))
    
    print("Flags status for this chunk:\n", flags)
    print('='*50)
    # Save the triggered entities to a CSV after processing completes
    triggered_df = pd.DataFrame(triggered_entities)
    # triggered_df.to_csv("files/triggered_entities.csv", index=False)

    return flags


# Global dictionary to store transcriptions for each room
room_transcriptions = {}
stop_flags = {}

# Function to periodically process transcriptions and generate chapter titles
def process_transcriptions_periodically(interval, transcriptions, room, processed_transcriptions=""):
    if stop_flags.get(room, False):
        print(f"Stopping processing for room {room}")
        return
    
    if transcriptions:
        # Combine all collected transcriptions
        new_transcriptions = ' '.join([entry['text'] for entry in transcriptions])
        
        # Combine newly collected transcriptions with previously processed ones
        combined_transcriptions = processed_transcriptions + ' ' + new_transcriptions
        
        print(f"Collected transcriptions for room {room}: {combined_transcriptions}")

        # Generate chapter titles based on the combined transcriptions
        chapter_titles = generate_chapter_titles(combined_transcriptions)
        print(f"Generated chapter titles for room {room}: {chapter_titles}")

        # Emit the chapter titles to the frontend
        socketio.emit('chapter_titles', {'titles': chapter_titles}, room=room)

        # Generate SOAP summary based on the combined transcriptions
        soap_summary = generate_soap_summary(combined_transcriptions)
        print(f"Generated soap summary for room {room}: {soap_summary}")

        # Emit the SOAP summary to the frontend
        socketio.emit('soap_summary', {'summary': soap_summary}, room=room)

        # Generate checkbox flags based on the new transcriptions
        checkbox_flags = generate_checkbox_flags(new_transcriptions)
        print(f"Generated checkbox flags for room {room}: {checkbox_flags}")

        # Emit the checkbox flags to the frontend
        socketio.emit('checkbox_flags', {'flags': checkbox_flags}, room=room)
    
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
        
        if room not in stop_flags:
            stop_flags[room] = False

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

        stop_flags[room] = True

        # Clear the stop flag list for this room
        stop_flags.pop(room, None)

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
