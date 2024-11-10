import numpy as np
import pyaudio
import nemo
import nemo.collections.asr as nemo_asr
import torch
import time

# Load the AmberNet model for spoken language identification
model_path = "C:/Users/adell/OneDrive/Documents/Capstone/pearlnet.nemo"
vad_model = nemo_asr.models.EncDecSpeakerLabelModel.restore_from(restore_path=model_path)

# Set model to evaluation mode
vad_model.eval()

# Parameters for PyAudio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Duration for which to collect audio data (in seconds)
duration = 5  # Collect audio data for 5 seconds
num_chunks = int(RATE / CHUNK * duration)  # Number of chunks to collect

# Language mapping
language_mapping = {
    0: 'Abkhazian', 1: 'Afrikaans', 2: 'Amharic', 3: 'Arabic', 4: 'Assamese', 5: 'Azerbaijani',
    6: 'Bashkir', 7: 'Belarusian', 8: 'Bulgarian', 9: 'Bengali', 10: 'Tibetan', 11: 'Breton',
    12: 'Bosnian', 13: 'Catalan', 14: 'Cebuano', 15: 'Czech', 16: 'Welsh', 17: 'Danish',
    18: 'German', 19: 'Greek', 20: 'English', 21: 'Esperanto', 22: 'Spanish', 23: 'Estonian',
    24: 'Basque', 25: 'Persian', 26: 'Finnish', 27: 'Faroese', 28: 'French', 29: 'Galician',
    30: 'Guarani', 31: 'Gujarati', 32: 'Manx', 33: 'Hausa', 34: 'Hawaiian', 35: 'Hindi',
    36: 'Croatian', 37: 'Haitian', 38: 'Hungarian', 39: 'Armenian', 40: 'Interlingua', 41: 'Indonesian',
    42: 'Icelandic', 43: 'Italian', 44: 'Hebrew', 45: 'Japanese', 46: 'Javanese', 47: 'Georgian',
    48: 'Kazakh', 49: 'Khmer', 50: 'Kannada', 51: 'Korean', 52: 'Latin', 53: 'Luxembourgish',
    54: 'Lingala', 55: 'Lao', 56: 'Lithuanian', 57: 'Latvian', 58: 'Malagasy', 59: 'Maori',
    60: 'Macedonian', 61: 'Malayalam', 62: 'Mongolian', 63: 'Marathi', 64: 'Malay', 65: 'Maltese',
    66: 'Burmese', 67: 'Nepali', 68: 'Dutch', 69: 'Norwegian', 70: 'Occitan', 71: 'Panjabi',
    72: 'Polish', 73: 'Pashto', 74: 'Portuguese', 75: 'Romanian', 76: 'Russian', 77: 'Sanskrit',
    78: 'Scottish Gaelic', 79: 'Sindhi', 80: 'Sinhalese', 81: 'Slovak', 82: 'Slovenian',
    83: 'Shona', 84: 'Somali', 85: 'Albanian', 86: 'Serbian', 87: 'Sundanese', 88: 'Swedish',
    89: 'Swahili', 90: 'Tamil', 91: 'Telugu', 92: 'Tajik', 93: 'Thai', 94: 'Turkmen',
    95: 'Tagalog', 96: 'Turkish', 97: 'Tatar', 98: 'Ukrainian', 99: 'Urdu', 100: 'Uzbek',
    101: 'Vietnamese', 102: 'Waray', 103: 'Yiddish', 104: 'Yoruba', 105: 'Chinese'
}

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Start streaming audio
stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

print("Listening...")

try:
    while True:
        # Initialize buffer to store audio data
        buffer = np.zeros(num_chunks * CHUNK, dtype=np.int16)

        # Collect audio data for the specified duration
        for i in range(num_chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            buffer[i * CHUNK:(i + 1) * CHUNK] = audio_data  # Fill buffer

        # Use the buffer directly for input without reshaping
        input_data = buffer

        # Prepare input length
        input_length = torch.tensor([input_data.shape[0]])  # Length of the audio input

        # Convert audio data to PyTorch tensor
        audio_data_tensor = torch.tensor(input_data, dtype=torch.float32).unsqueeze(0)  # Add batch dimension

        # Perform language identification
        predicted_language = vad_model.forward(input_signal=audio_data_tensor, input_signal_length=input_length)

        # Apply softmax to get probabilities
        probabilities = torch.softmax(predicted_language[0], dim=-1)

        # Get top 3 probabilities and their indices
        top_k = torch.topk(probabilities, 3)

        # Print the top 3 detected languages and their probabilities
        for i in range(top_k.indices.shape[1]):
            language_index = top_k.indices[0][i].item()
            probability = top_k.values[0][i].item()
            detected_language = language_mapping.get(language_index, "Unknown")
            print(f"Detected Language: {detected_language}, Probability: {probability:.4f}")
        print()
        # Wait for a while before the next iteration (if needed)
        time.sleep(1)  # Optional delay before starting the next 5 seconds collection

except KeyboardInterrupt:
    print("Stopping...")

finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
