from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import whisper
import torch
import numpy as np
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
from pyannote.audio import Audio
from pyannote.core import Segment
from sklearn.cluster import AgglomerativeClustering
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Load models
model = whisper.load_model("large")  # Whisper model size
embedding_model = PretrainedSpeakerEmbedding("speechbrain/spkrec-ecapa-voxceleb", device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
audio = Audio()

# Store recognizers and streams for each room
recognizers = {}
audio_streams = {}

@app.route('/start_transcription', methods=['POST'])
def start_transcription():
    room = request.json.get("room")
    if room:
        recognizers[room] = []  # To store audio segments for this room
        return {"message": "Transcription started"}, 200
    else:
        return {"error": "Room not specified"}, 400

@app.route('/stop_transcription', methods=['POST'])
def stop_transcription():
    room = request.json.get("room")
    if room:
        if room in recognizers:
            transcribe_and_diarize(room)  # Call the Whisper and diarization function
            del recognizers[room]
        return {"message": "Transcription stopped"}, 200
    else:
        return {"error": "Room not specified"}, 400

@socketio.on('audio_data')
def handle_audio_data(data):
    room = data['room']
    audio_data = data['audio_data']  # Audio data from the client
    if room in recognizers:
        recognizers[room].append(audio_data)
    else:
        app.logger.error("Audio stream for the room not found")

def transcribe_and_diarize(room):
    audio_data = b''.join(recognizers[room])
    
    # Convert audio data to waveform and normalize it
    waveform = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
    
    # Ensure waveform is 2D (1, time)
    waveform = torch.from_numpy(waveform).unsqueeze(0)
    
    # Use Whisper for transcription
    transcription_result = model.transcribe(waveform, language='en')
    
    # Debug: Inspect transcription result
    print(transcription_result)
    
    segments = transcription_result["segments"]

    # Use PyAnnote for speaker embedding and clustering
    embeddings = np.zeros((len(segments), 192))
    for i, segment in enumerate(segments):
        start = segment["start"]
        end = min(waveform.shape[1] / 16000, segment["end"])  # 16000 is the sample rate
        clip = Segment(start, end)
        waveform_segment, _ = audio.crop({'waveform': waveform, 'sample_rate': 16000}, clip)
        embeddings[i] = embedding_model(waveform_segment[None])

    embeddings = np.nan_to_num(embeddings)
    clustering = AgglomerativeClustering(n_clusters=2).fit(embeddings)
    labels = clustering.labels_

    for i in range(len(segments)):
        segments[i]["speaker"] = 'SPEAKER ' + str(labels[i] + 1)

    # Print or save the transcription with speaker labels
    for segment in segments:
        print(f'{segment["speaker"]}: {segment["text"]}')

def auto_transcribe():
    while True:
        socketio.sleep(30)  # Wait for 30 seconds
        for room in recognizers.keys():
            transcribe_and_diarize(room)

if __name__ == '__main__':
    threading.Thread(target=auto_transcribe, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=8000)
