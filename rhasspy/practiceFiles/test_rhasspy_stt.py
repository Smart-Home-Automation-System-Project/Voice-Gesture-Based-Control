# filepath: test_rhasspy_stt.py
import requests
import sys

RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
WAV_FILE = "test_audio.wav" # Make sure this file exists

def transcribe_audio(file_path):
    """Sends audio data to Rhasspy's STT endpoint."""
    try:
        with open(file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        print(f"Sending audio data from {file_path} to Rhasspy STT...")
        # Send audio data as POST request body
        # Set Content-Type header to audio/wav
        headers = {'Content-Type': 'audio/wav'}
        response = requests.post(STT_ENDPOINT, headers=headers, data=audio_data, timeout=20) # Increased timeout for STT

        print(f"Request sent. Status code: {response.status_code}")
        response.raise_for_status() # Raise an exception for bad status codes

        transcribed_text = response.text # Rhasspy returns plain text
        print(f"Transcription result: '{transcribed_text}'")
        return transcribed_text

    except FileNotFoundError:
        print(f"Error: Audio file not found at '{file_path}'", file=sys.stderr)
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
    transcription = transcribe_audio(WAV_FILE)
    if transcription:
        print("STT test successful.")
    else:
        print("STT test failed.")
    print("Script finished.")