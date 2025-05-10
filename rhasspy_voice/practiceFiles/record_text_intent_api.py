import requests
import sys
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import io
import json
import os

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent" # Endpoint for intent recognition from text

# Recording parameters
SAMPLE_RATE = 16000  # Hz
DURATION = 5       # seconds
CHANNELS = 1       # mono
RECORDING_FILENAME = "last_recording_api.wav" # Filename to save recording

# --- Audio Recording ---
def record_audio(duration, samplerate, channels):
    """Records audio from the default microphone."""
    print(f"Recording for {duration} seconds...")
    try:
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
        sd.wait()
        print("Recording finished.")
        wav_buffer = io.BytesIO()
        write(wav_buffer, samplerate, recording)
        wav_buffer.seek(0)
        return wav_buffer.read() # Return the raw WAV bytes
    except Exception as e:
        print(f"Error during recording: {e}", file=sys.stderr)
        return None

# --- Send Audio to Rhasspy STT ---
def get_text_from_audio(audio_data):
    """Sends audio data (bytes) to Rhasspy's STT endpoint and returns the text."""
    if not audio_data:
        print("No audio data to send.", file=sys.stderr)
        return None
    print("Sending recorded audio data to Rhasspy STT...")
    try:
        headers = {'Content-Type': 'audio/wav'}
        response = requests.post(STT_ENDPOINT, headers=headers, data=audio_data, timeout=20)
        print(f"STT request sent. Status code: {response.status_code}")
        response.raise_for_status()
        transcribed_text = response.text
        print(f"STT API Result (text): '{transcribed_text}'")
        return transcribed_text # Return the transcribed text
    except requests.exceptions.Timeout:
         print("Error: The request to Rhasspy STT timed out.", file=sys.stderr)
    except requests.exceptions.ConnectionError:
         print(f"Error: Could not connect to Rhasspy STT at {STT_ENDPOINT}. Is it running?", file=sys.stderr)
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Rhasspy STT: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response content: {e.response.text}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during STT request: {e}", file=sys.stderr)
    return None # Indicate failure

# --- Get Intent from Text ---
def get_intent_from_text(text):
    """Sends text to Rhasspy's NLU endpoint and returns the intent JSON."""
    if not text:
        print("No text provided for intent recognition.", file=sys.stderr)
        return None
    print(f"Sending text '{text}' to Rhasspy NLU...")
    try:
        # Send text as plain text in the POST body
        response = requests.post(NLU_ENDPOINT, data=text.encode('utf-8'), timeout=10)
        print(f"NLU request sent. Status code: {response.status_code}")
        response.raise_for_status()
        intent_data = response.json() # Parse the JSON response
        print(f"NLU API Result (JSON): {json.dumps(intent_data, indent=2)}")
        return intent_data
    except requests.exceptions.Timeout:
         print("Error: The request to Rhasspy NLU timed out.", file=sys.stderr)
    except requests.exceptions.ConnectionError:
         print(f"Error: Could not connect to Rhasspy NLU at {NLU_ENDPOINT}. Is it running?", file=sys.stderr)
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Rhasspy NLU: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response content: {e.response.text}", file=sys.stderr)
    except json.JSONDecodeError:
        print("Error decoding JSON response from NLU endpoint.", file=sys.stderr)
        print(f"Raw response: {response.text}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during NLU request: {e}", file=sys.stderr)
    return None

# --- Main Execution ---
if __name__ == "__main__":
    try:
        # 1. Record audio
        recorded_wav_data = record_audio(DURATION, SAMPLE_RATE, CHANNELS)

        if recorded_wav_data:
            # --- Save the recording locally (optional) ---
            try:
                print(f"Saving recording to {RECORDING_FILENAME}...")
                with open(RECORDING_FILENAME, "wb") as f:
                    f.write(recorded_wav_data)
                print(f"File saved successfully. Size: {os.path.getsize(RECORDING_FILENAME)} bytes")
            except Exception as e_write:
                print(f"Error saving recording file '{RECORDING_FILENAME}': {e_write}", file=sys.stderr)
            # --- End of saving section ---

            # 2. Get text transcription from audio
            transcribed_text = get_text_from_audio(recorded_wav_data)

            if transcribed_text:
                # 3. Get intent from the transcribed text
                intent_result = get_intent_from_text(transcribed_text)

                if intent_result and intent_result.get('intent'):
                    intent_name = intent_result['intent'].get('name', 'UnknownIntent')
                    confidence = intent_result['intent'].get('confidence', 'N/A')
                    print("\n--- Final Recognized Intent (via API) ---")
                    print(f"Intent: {intent_name}")
                    print(f"Confidence: {confidence}")
                    # You can access slots/entities via intent_result['entities'] if needed
                    print("-----------------------------------------")
                elif intent_result:
                     print("NLU endpoint returned a result, but no intent was recognized.", file=sys.stderr)
                     print(f"Full NLU Response: {json.dumps(intent_result, indent=2)}")
                else:
                    print("Failed to get intent from NLU endpoint.", file=sys.stderr)
            else:
                print("STT failed. Cannot proceed to intent recognition.", file=sys.stderr)
        else:
             print("Audio recording failed.", file=sys.stderr)

    except Exception as e:
        print(f"An unexpected error occurred in main execution: {e}", file=sys.stderr)
    finally:
        print("Script finished.")