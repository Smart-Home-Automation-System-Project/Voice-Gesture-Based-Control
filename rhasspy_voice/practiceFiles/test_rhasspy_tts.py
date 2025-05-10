# filepath: test_rhasspy_tts.py
import requests
import json
import sys # Import sys module

RHASSPY_URL = "http://localhost:12101"
TTS_ENDPOINT = f"{RHASSPY_URL}/api/text-to-speech"

def speak_text(text):
    """Sends text to Rhasspy's TTS endpoint."""
    print("Attempting to send text to Rhasspy...") # Added print
    try:
        response = requests.post(TTS_ENDPOINT, data=text, timeout=10) # Added timeout
        print(f"Request sent. Status code: {response.status_code}") # Added print
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Rhasspy should be speaking: '{text}'")
        # The audio data is in response.content if you wanted to save/play it manually
        # For this setup, Rhasspy plays it directly through the configured audio output.
    except requests.exceptions.Timeout:
         print("Error: The request to Rhasspy timed out.", file=sys.stderr) # Added timeout exception
    except requests.exceptions.ConnectionError:
         print(f"Error: Could not connect to Rhasspy at {TTS_ENDPOINT}. Is it running?", file=sys.stderr) # Added connection error
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Rhasspy TTS: {e}", file=sys.stderr) # Print to stderr
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr) # Print to stderr

if __name__ == "__main__":
    text_to_say = "Hello, Rhasspy is working."
    speak_text(text_to_say)
    print("Script finished.") # Added print