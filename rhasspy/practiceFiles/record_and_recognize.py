import requests
import sys
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import io
import paho.mqtt.client as mqtt
import json
import time
import threading
import os # Import os module for file operations

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
RHASSPY_MQTT_HOST = "localhost"
RHASSPY_MQTT_PORT = 1883 #  MQTT port
INTENT_TOPIC = "hermes/intent/#" # Subscribe to all intents

# Recording parameters
SAMPLE_RATE = 16000  # Hz
DURATION = 5       # seconds
CHANNELS = 1       # mono
RECORDING_FILENAME = "last_recording.wav" # Filename to save recording

# --- Global variables for MQTT ---
mqtt_client = None
last_intent = None
intent_received_event = threading.Event() # To signal when an intent is received

# --- Audio Recording ---
def record_audio(duration, samplerate, channels):
    """Records audio from the default microphone."""
    print(f"Recording for {duration} seconds...")
    try:
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
        sd.wait()
        print("Recording finished.")
        wav_buffer = io.BytesIO()
        # Use scipy to write WAV format into the buffer
        write(wav_buffer, samplerate, recording)
        wav_buffer.seek(0)
        return wav_buffer.read() # Return the raw WAV bytes
    except Exception as e:
        print(f"Error during recording: {e}", file=sys.stderr)
        # You might want to call list_audio_devices() here again for debugging
        return None

# --- Send Audio to Rhasspy STT ---
def send_audio_for_stt(audio_data):
    """Sends audio data (bytes) to Rhasspy's STT endpoint."""
    if not audio_data:
        print("No audio data to send.", file=sys.stderr)
        return False
    print("Sending recorded audio data to Rhasspy STT...")
    try:
        headers = {'Content-Type': 'audio/wav'}
        response = requests.post(STT_ENDPOINT, headers=headers, data=audio_data, timeout=20)
        print(f"STT request sent. Status code: {response.status_code}")
        response.raise_for_status()
        # We don't strictly need the transcription text here,
        # as we'll get the intent via MQTT.
        # transcribed_text = response.text
        # print(f"STT API Result (text): '{transcribed_text}'")
        return True # Indicate success
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
    return False # Indicate failure

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to MQTT broker (version 2 API)."""
    # The reason_code provides more detailed connection results.
    # rc=0 corresponds to reason_code=0 (Success)
    if reason_code == 0:
        print(f"Connected to MQTT broker (Reason Code: {reason_code})")
        # Subscribe here is fine for simple cases
        client.subscribe(INTENT_TOPIC)
        print(f"Subscribed to topic: {INTENT_TOPIC}")
    else:
        # You can check paho.mqtt.reasoncodes for specific error meanings
        print(f"Failed to connect to MQTT broker (Reason Code: {reason_code})", file=sys.stderr)

def on_message(client, userdata, msg):
    """Callback when an intent message is received."""
    global last_intent
    print("-" * 20)
    print(f"Received MQTT message on topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        intent_name = payload.get('intent', {}).get('intentName', 'UnknownIntent')
        confidence = payload.get('intent', {}).get('confidenceScore', 'N/A')

        print(f"Intent Detected via MQTT: {intent_name}")
        print(f"Confidence: {confidence}")

        # Store the relevant info and signal that we received it
        last_intent = {'name': intent_name, 'confidence': confidence, 'payload': payload}
        intent_received_event.set() # Signal the main thread

    except json.JSONDecodeError:
        print("Error decoding JSON payload from MQTT.")
        print(f"Raw payload: {msg.payload}")
    except Exception as e:
        print(f"An error occurred processing the MQTT message: {e}", file=sys.stderr)
    print("-" * 20)

# --- Main Execution ---
if __name__ == "__main__":
    # Initialize MQTT Client
    # Use Callback API version 2
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        print(f"Attempting to connect to MQTT broker at {RHASSPY_MQTT_HOST}:{RHASSPY_MQTT_PORT}...")
        mqtt_client.connect(RHASSPY_MQTT_HOST, RHASSPY_MQTT_PORT, 60)
        mqtt_client.loop_start() # Start MQTT loop in background thread
        time.sleep(1) # Give time for connection and subscription

        # 1. Record audio
        recorded_wav_data = record_audio(DURATION, SAMPLE_RATE, CHANNELS)

        if recorded_wav_data:
            # --- Save the recording locally ---
            try:
                print(f"Saving recording to {RECORDING_FILENAME}...")
                with open(RECORDING_FILENAME, "wb") as f:
                    f.write(recorded_wav_data)
                print(f"File saved successfully. Size: {os.path.getsize(RECORDING_FILENAME)} bytes")
            except Exception as e_write:
                print(f"Error saving recording file '{RECORDING_FILENAME}': {e_write}", file=sys.stderr)
            # --- End of saving section ---

            # Clear previous intent and reset event before sending audio
            last_intent = None
            intent_received_event.clear()

            # 2. Send audio for STT (which triggers intent recognition)
            stt_success = send_audio_for_stt(recorded_wav_data)

            if stt_success:
                # 3. Wait for the intent result via MQTT (with a timeout)
                print("Waiting for intent result via MQTT...")
                received = intent_received_event.wait(timeout=10) # Wait up to 10 seconds

                if received and last_intent:
                    print("\n--- Final Recognized Intent ---")
                    print(f"Intent: {last_intent['name']}")
                    print(f"Confidence: {last_intent['confidence']}")
                    # print("Full Payload:")
                    # print(json.dumps(last_intent['payload'], indent=2))
                    print("-------------------------------")
                elif received and not last_intent:
                     print("Intent message received, but data processing failed.", file=sys.stderr)
                else:
                    print("Timeout: No intent message received via MQTT within 10 seconds.", file=sys.stderr)
            else:
                print("STT request failed. Cannot proceed to intent recognition.", file=sys.stderr)
        else:
             print("Audio recording failed.", file=sys.stderr)

    except ConnectionRefusedError:
        print(f"Error: Connection to MQTT broker refused. Is Rhasspy running and MQTT enabled?", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred in main execution: {e}", file=sys.stderr)
    finally:
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.loop_stop() # Stop MQTT background thread
            mqtt_client.disconnect()
            print("\nMQTT client stopped and disconnected.")
        elif mqtt_client:
             # If loop wasn't started (e.g., connection failed), still try to clean up
             try:
                 mqtt_client.disconnect()
             except Exception:
                 pass # Ignore errors during cleanup disconnect
             print("\nMQTT client stopped (was not connected or loop not started).")

        print("Script finished.")
