import requests
import sys
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import io
import json
import os
import paho.mqtt.client as mqtt
import time
import threading

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent"

# Rhasspy Internal MQTT (for wake word detection)
# This script will connect to the same MQTT broker Rhasspy uses.
# Ensure Rhasspy is configured to output to this broker.
RHASSPY_MQTT_HOST = "localhost"
RHASSPY_MQTT_PORT = 1883 # Default for Mosquitto. If Rhasspy uses its internal broker, it might be 12183.
WAKE_WORD_TOPIC = "hermes/hotword/+/detected" # Standard Hermes topic for wake word

# External MQTT (for publishing results - now also local)
EXTERNAL_MQTT_BROKER = "localhost" # Changed to localhost
EXTERNAL_MQTT_PORT = 1883
EXTERNAL_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized"

# Recording parameters
SAMPLE_RATE = 16000  # Hz
COMMAND_DURATION = 5 # Seconds to record command after wake word
CHANNELS = 1       # mono
RECORDING_FILENAME = "last_command_recording.wav" # Optional: for debugging

# --- State ---
is_processing = False # Flag to prevent processing multiple commands at once
processing_lock = threading.Lock()

# --- MQTT Clients ---
rhasspy_listen_client = None # For listening to Rhasspy's wake word
intent_publish_client = None # For publishing recognized intents

# --- MQTT Callbacks (For Rhasspy Wake Word Listener) ---
def on_connect_rhasspy_listener(client, userdata, flags, reason_code, properties):
    """Callback when connected to MQTT for listening to Rhasspy."""
    if reason_code == 0:
        print(f"Connected to MQTT for Rhasspy wake word ({RHASSPY_MQTT_HOST}:{RHASSPY_MQTT_PORT})")
        client.subscribe(WAKE_WORD_TOPIC)
        print(f"Subscribed to Rhasspy wake word topic: {WAKE_WORD_TOPIC}")
    else:
        print(f"Failed to connect to MQTT for Rhasspy wake word, reason code {reason_code}", file=sys.stderr)

def on_message_rhasspy_listener(client, userdata, msg):
    """Callback when a message (wake word) is received from Rhasspy's MQTT."""
    global is_processing
    # Basic check for wake word topic structure
    if msg.topic.startswith("hermes/hotword/") and msg.topic.endswith("/detected"):
        with processing_lock:
            if is_processing:
                print("Wake word detected, but already processing a command. Ignoring.")
                return
            is_processing = True # Set flag immediately

        print("-" * 30)
        print(f"Wake word detected on topic: {msg.topic}")
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            print(f"Wake word siteId: {payload.get('siteId', 'N/A')}")
        except json.JSONDecodeError:
            print("Could not decode wake word payload as JSON.")
        except Exception as e:
            print(f"Error processing wake word payload: {e}")


        # Trigger the command processing in a separate thread
        # to avoid blocking the MQTT loop
        thread = threading.Thread(target=handle_command_after_wake)
        thread.daemon = True # Allow main program to exit even if threads are running
        thread.start()
        print("Started command handling thread.")
        print("-" * 30)

# --- MQTT Callbacks (For Publishing Intents) ---
def on_connect_intent_publisher(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to MQTT for publishing intents ({EXTERNAL_MQTT_BROKER}:{EXTERNAL_MQTT_PORT})")
    else:
        print(f"Failed to connect to MQTT for publishing intents, reason code {reason_code}", file=sys.stderr)

def on_publish_intent_publisher(client, userdata, mid, reason_code, properties):
    # print(f"Intent message {mid} published (Reason Code: {reason_code})")
    pass

# --- Audio & Processing Functions ---
def record_audio(duration, samplerate, channels):
    print(f"Listening for command ({duration} seconds)...")
    try:
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
        sd.wait()
        print("Command recording finished.")
        wav_buffer = io.BytesIO()
        write(wav_buffer, samplerate, recording)
        wav_buffer.seek(0)
        return wav_buffer.read()
    except Exception as e:
        print(f"Error during command recording: {e}", file=sys.stderr)
        return None

def get_text_from_audio(audio_data):
    if not audio_data: return None
    print("Sending command audio to Rhasspy STT...")
    try:
        headers = {'Content-Type': 'audio/wav'}
        response = requests.post(STT_ENDPOINT, headers=headers, data=audio_data, timeout=20)
        response.raise_for_status()
        transcribed_text = response.text.strip() # .strip() to remove potential newlines
        if not transcribed_text:
            print("STT API Result: Empty transcription")
            return None
        print(f"STT API Result (text): '{transcribed_text}'")
        return transcribed_text
    except requests.exceptions.RequestException as e:
        print(f"Error during STT request: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error during STT: {e}", file=sys.stderr)
        return None


def get_intent_from_text(text):
    if not text: return None
    print(f"Sending text '{text}' to Rhasspy NLU...")
    try:
        response = requests.post(NLU_ENDPOINT, data=text.encode('utf-8'), timeout=10)
        response.raise_for_status()
        intent_data = response.json()
        print(f"NLU API Result (JSON): {json.dumps(intent_data, indent=2)}")
        return intent_data
    except requests.exceptions.RequestException as e:
        print(f"Error during NLU request: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"NLU API Result: Not valid JSON: {response.text}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error during NLU: {e}", file=sys.stderr)
        return None

def publish_intent(topic, intent_name, confidence, slots=None):
    global intent_publish_client
    if not intent_publish_client or not intent_publish_client.is_connected():
        print("Intent publishing MQTT client not connected. Cannot publish intent.", file=sys.stderr)
        return
    message_dict = {"intent": intent_name, "confidence": confidence}
    if slots:
        message_dict["slots"] = slots
    message_json = json.dumps(message_dict)
    result = intent_publish_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Intent published to MQTT topic {topic}: {message_json}")
    else:
        print(f"Failed to send message to MQTT topic {topic} (Error code: {status})", file=sys.stderr)

# --- Command Handling Logic ---
def handle_command_after_wake():
    """Records audio, gets intent, publishes, then resets processing flag."""
    global is_processing
    try:
        command_audio = record_audio(COMMAND_DURATION, SAMPLE_RATE, CHANNELS)

        if command_audio:
            # Optional: Save recording for debugging
            # try:
            #     with open(RECORDING_FILENAME, "wb") as f: f.write(command_audio)
            #     print(f"Command recording saved to {RECORDING_FILENAME}")
            # except Exception as e_write: print(f"Error saving recording: {e_write}", file=sys.stderr)

            text = get_text_from_audio(command_audio)

            if text:
                intent_result = get_intent_from_text(text)

                if intent_result and intent_result.get('intent') and intent_result['intent'].get('name'):
                    intent_name = intent_result['intent']['name']
                    confidence = intent_result['intent'].get('confidence', 0.0) # Default to 0.0
                    slots = intent_result.get('slots', {})
                    print("\n--- Recognized Intent ---")
                    print(f"Intent: {intent_name}")
                    print(f"Confidence: {confidence:.2f}")
                    if slots: print(f"Slots: {slots}")
                    print("-------------------------")

                    publish_intent(EXTERNAL_MQTT_INTENT_TOPIC, intent_name, confidence, slots)
                else:
                    print("Could not recognize a valid intent from text.", file=sys.stderr)
                    if intent_result: print(f"NLU Raw Output: {intent_result}")
            else:
                print("Could not transcribe audio to text.", file=sys.stderr)
        else:
            print("Failed to record command audio.", file=sys.stderr)

    except Exception as e:
        print(f"An error occurred in handle_command_after_wake: {e}", file=sys.stderr)
    finally:
        with processing_lock:
            is_processing = False # Reset flag
        print("Ready for next wake word.")

# --- Main Execution ---
if __name__ == "__main__":
    # Initialize MQTT Client for listening to Rhasspy wake words
    rhasspy_listen_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="jarvis_wake_listener")
    rhasspy_listen_client.on_connect = on_connect_rhasspy_listener
    rhasspy_listen_client.on_message = on_message_rhasspy_listener

    # Initialize MQTT Client for publishing recognized intents
    intent_publish_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="jarvis_intent_publisher")
    intent_publish_client.on_connect = on_connect_intent_publisher
    intent_publish_client.on_publish = on_publish_intent_publisher

    try:
        # Connect to MQTT for publishing intents
        print(f"Connecting to MQTT for publishing intents ({EXTERNAL_MQTT_BROKER}:{EXTERNAL_MQTT_PORT})...")
        intent_publish_client.connect(EXTERNAL_MQTT_BROKER, EXTERNAL_MQTT_PORT, 60)
        intent_publish_client.loop_start() # Non-blocking

        # Connect to MQTT for listening to Rhasspy wake words
        print(f"Connecting to MQTT for Rhasspy wake word ({RHASSPY_MQTT_HOST}:{RHASSPY_MQTT_PORT})...")
        rhasspy_listen_client.connect(RHASSPY_MQTT_HOST, RHASSPY_MQTT_PORT, 60)

        print("Listening for wake word via Rhasspy MQTT... Press Ctrl+C to stop.")
        rhasspy_listen_client.loop_forever() # Blocking loop for the listener

    except ConnectionRefusedError as e:
        print(f"MQTT Connection Refused: {e}. Check broker address/port and if Rhasspy/broker is running.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nStopping script...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        print("Cleaning up MQTT clients...")
        if rhasspy_listen_client:
            rhasspy_listen_client.loop_stop() # Stop network loop
            rhasspy_listen_client.disconnect()
            print("Rhasspy wake word MQTT client stopped and disconnected.")
        if intent_publish_client:
            intent_publish_client.loop_stop()
            intent_publish_client.disconnect()
            print("Intent publishing MQTT client stopped and disconnected.")
        print("Script finished.")