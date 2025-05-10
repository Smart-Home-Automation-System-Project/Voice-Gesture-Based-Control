import requests
import sys
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import io
import json
import os
import paho.mqtt.client as mqtt # Import MQTT client
import time

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent" # Endpoint for intent recognition from text

# MQTT Configuration
MQTT_BROKER = "test.mosquitto.org"  # Public MQTT broker for testing
MQTT_PORT = 1883
MQTT_INTENT_TOPIC = "rhasspy/intent/recognized" # Topic to publish recognized intents

# Recording parameters
SAMPLE_RATE = 16000  # Hz
DURATION = 5       # seconds
CHANNELS = 1       # mono
RECORDING_FILENAME = "last_recording_api.wav" # Filename to save recording

# --- MQTT Client Setup ---
mqtt_client = None

# MQTT Callbacks
def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to MQTT broker."""
    if reason_code == 0:
        print(f"Connected to MQTT Broker: {MQTT_BROKER}")
    else:
        print(f"Failed to connect to MQTT Broker, return code {reason_code}")

def on_publish(client, userdata, mid, reason_code, properties):
    """Callback when a message is published."""
    # reason_code is None for MQTT v3.1/3.1.1 QoS 0 publishes.
    # For QoS 1/2, it indicates success/failure.
    # mid is the message ID.
    # print(f"Message {mid} published (Reason Code: {reason_code})")
    pass # Keep it quiet unless debugging

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

# --- MQTT Publish Function ---
def publish_intent(topic, intent_name, confidence):
    """Publishes the recognized intent to the specified MQTT topic."""
    global mqtt_client
    if not mqtt_client or not mqtt_client.is_connected():
        print("MQTT client not connected. Cannot publish intent.", file=sys.stderr)
        return

    message_dict = {
        "intent": intent_name,
        "confidence": confidence
        # Add slots/entities here if needed: "entities": intent_result.get('entities', [])
    }
    message_json = json.dumps(message_dict)
    result = mqtt_client.publish(topic, message_json)
    status = result.rc # rc attribute holds the result code
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Intent published to MQTT topic {topic}: {message_json}")
    else:
        print(f"Failed to send message to topic {topic} (Error code: {status})")


# --- Main Execution ---
if __name__ == "__main__":
    # Initialize MQTT Client
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_publish = on_publish

    try:
        # Connect to MQTT Broker
        print(f"Connecting to MQTT broker {MQTT_BROKER}...")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start() # Start background thread for MQTT
        time.sleep(1) # Allow time for connection

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
                    print("-----------------------------------------")

                    # 4. Publish the recognized intent via MQTT
                    publish_intent(MQTT_INTENT_TOPIC, intent_name, confidence)

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
        # Clean up MQTT client
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            print("\nMQTT client stopped and disconnected.")
        elif mqtt_client:
             try:
                 mqtt_client.disconnect() # Attempt disconnect even if loop wasn't started
             except Exception:
                 pass
             print("\nMQTT client stopped (was not connected or loop not started).")

        print("Script finished.")