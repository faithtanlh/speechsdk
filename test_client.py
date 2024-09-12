import requests
import socketio
import pyaudio

# SocketIO client setup
sio = socketio.Client()

# Audio setup
FORMAT = pyaudio.paInt16  # 16-bit audio format
CHANNELS = 1  # Mono audio
RATE = 16000  # Sample rate
CHUNK = 1024  # Size of each audio chunk

p = pyaudio.PyAudio()

# Define the test server URL
server_url = 'http://localhost:8000'

# Function to start transcription
def start_transcription(room):
    url = f"{server_url}/start_transcription"
    data = {"room": room}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print("Transcription started successfully.")
        else:
            print(f"Failed to start transcription: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with the server: {e}")

# Function to end transcription
def end_transcription(room):
    url = f"{server_url}/end_transcription"
    data = {"room": room}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print("Transcription ended successfully.")
        else:
            print(f"Failed to end transcription: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with the server: {e}")

# Function to start streaming audio
def start_streaming(room):

    # Callback for capturing and sending audio data
    def stream_audio(in_data, frame_count, time_info, status):
        sio.emit('audio_data', {"room": room, "audio_data": in_data})  # Send the audio chunk to the server
        return (in_data, pyaudio.paContinue)

    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, stream_callback=stream_audio)
    print("Recording and streaming audio")
    stream.start_stream()

    try:
        # Keep the stream running
        while stream.is_active():
            pass
    except KeyboardInterrupt:
        print("Keyboard interrupt detected, stopping audio stream")
    finally:
        # Clean up the stream
        stream.stop_stream()
        stream.close()

@sio.event
def join_room(data):
    room_id = data["room"]
    print(f"Connected to server with Room ID {room_id}")
    start_transcription(room_id)

    try:
        start_streaming(room_id)
    except Exception as err:
        end_transcription(room_id)

@sio.event
def connect():
    print("Connected to server")

@sio.event
def disconnect():
    print("Disconnected from server")

if __name__ == "__main__":
    sio.connect(server_url)
    # Keep the connection open
    while True:
        pass

