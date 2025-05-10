# filepath: /home/k-indunil/Rhasspy0.1/record_and_transcribe.py
import requests
import sys
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import io
import os

RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"

# Recording parameters
SAMPLE_RATE = 16000  # Hz (Rhasspy usually prefers 16kHz)
DURATION = 5       # seconds
CHANNELS = 1       # mono

def list_audio_devices():
    """Prints available input/output audio devices."""
    print("--- Available Audio Devices ---")
    try:
        print(sd.query_devices())
    except Exception as e:
        print(f"Could not query audio devices: {e}", file=sys.stderr)
    print("--- Default Input Device ---")
    try:
        print(sd.query_devices(kind='input'))
    except Exception as e:
        print(f"Could not query default input device: {e}", file=sys.stderr)
    print("-----------------------------")

def record_audio(duration, samplerate, channels):
    """Records audio from the default microphone."""
    print(f"Recording for {duration} seconds...")
    try:
        # Record audio using sounddevice
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
        sd.wait()  # Wait until recording is finished
        print("Recording finished.")

        # Save the file for checking
        temp_filename = "temp_recording.wav"
        print(f"Saving recording to {temp_filename} for checking...")
        try:
            write(temp_filename, samplerate, recording)
            print(f"File saved successfully. Size: {os.path.getsize(temp_filename)} bytes")
            # Playback check (optional, requires aplay)
            # os.system(f"aplay {temp_filename}")
        except Exception as e_write:
            print(f"Error saving temporary WAV file: {e_write}", file=sys.stderr)

        # Convert the NumPy array to WAV format in memory
        wav_buffer = io.BytesIO()
        write(wav_buffer, samplerate, recording)
        wav_buffer.seek(0) # Rewind the buffer to the beginning
        return wav_buffer.read() # Return the raw WAV bytes

    except Exception as e:
        print(f"Error during recording: {e}", file=sys.stderr)
        return None

def transcribe_audio_data(audio_data):
    """Sends audio data (bytes) to Rhasspy's STT endpoint."""
    if not audio_data:
        print("No audio data received for transcription.", file=sys.stderr)
        return None
    try:
        print("Sending recorded audio data to Rhasspy STT...")
        # Send audio data as POST request body
        # Set Content-Type header to audio/wav
        headers = {'Content-Type': 'audio/wav'}
        response = requests.post(STT_ENDPOINT, headers=headers, data=audio_data, timeout=20)

        print(f"Request sent. Status code: {response.status_code}")
        response.raise_for_status() # Raise an exception for bad status codes

        transcribed_text = response.text # Rhasspy returns plain text
        print(f"Transcription result: '{transcribed_text}'")
        return transcribed_text

    except requests.exceptions.Timeout:
         print("Error: The request to Rhasspy STT timed out.", file=sys.stderr)
    except requests.exceptions.ConnectionError:
         print(f"Error: Could not connect to Rhasspy at {STT_ENDPOINT}. Is it running?", file=sys.stderr)
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Rhasspy STT: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response content: {e.response.text}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    return None

if __name__ == "__main__":
    # List devices first
    list_audio_devices()

    # 1. Record audio from microphone
    recorded_wav_data = record_audio(DURATION, SAMPLE_RATE, CHANNELS)

    # 2. Transcribe the recorded audio
    if recorded_wav_data:
        # Check if data is mostly silence (optional advanced check)
        # audio_array = np.frombuffer(recorded_wav_data[44:], dtype=np.int16) # Skip WAV header
        # if np.max(np.abs(audio_array)) < 500: # Threshold for silence might need adjustment
        #     print("Warning: Recorded audio seems very quiet or silent.", file=sys.stderr)

        transcription = transcribe_audio_data(recorded_wav_data)
        if transcription is not None and transcription != '': # Check for non-empty transcription
            print("Live STT test successful.")
        else:
            print(f"Live STT test failed (Transcription: '{transcription}').") # Show transcription result
    else:
         print("Live STT test failed (recording step).")

    print("Script finished.")