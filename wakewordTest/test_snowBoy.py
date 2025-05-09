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
import collections # For potential future use with audio buffering, not strictly needed here

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent"

# MQTT for listening to Rhasspy's Wake Word
RHASSPY_MQTT_BROKER = "localhost"
RHASSPY_MQTT_PORT = 1883
# Use a wildcard for siteId unless you have a very specific setup
RHASSPY_WAKE_WORD_TOPIC = "hermes/hotword/+/detected"
# This should match the 'wakewordId' you expect Rhasspy to send.
# For snowboy, if wake.hermes.wakeword_id is not set in profile.json,
# it might default to the model name (e.g., "jarvis") or a generic ID.
# Check Rhasspy logs or an MQTT explorer to see what it actually sends.
EXPECTED_WAKEWORD_ID = "jarvis" # Adjust if Rhasspy sends a different ID for your model

# MQTT for publishing recognized intents
EXTERNAL_MQTT_BROKER = "localhost"
EXTERNAL_MQTT_PORT = 1883
EXTERNAL_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized"

# Audio Recording parameters
SAMPLE_RATE = 16000  # Hz
CHANNELS = 1       # mono
COMMAND_DURATION = 5 # Seconds to record command AFTER wake word

# --- Global State ---
is_processing_command = False
processing_lock = threading.Lock()

# --- MQTT Clients ---
rhasspy_listener_client = None
intent_publisher_client = None

# --- MQTT Callbacks (Intent Publisher) ---
def on_connect_intent_publisher(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to Intent Publishing MQTT Broker: {EXTERNAL_MQTT_BROKER}")
    else:
        print(f"Failed to connect to Intent Publishing MQTT Broker, reason code {reason_code}")

def on_publish_intent_publisher(client, userdata, mid, reason_code, properties):
    # print(f"Intent publish acknowledged by broker (mid: {mid}, reason_code: {reason_code})")
    pass # Keep it quiet

# --- Audio & Processing Functions ---
def record_command_audio(duration, samplerate, channels):
    print(f"Listening for command ({duration} seconds)...")
    try:
        command_recording_np = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
        sd.wait()  # Wait for recording to complete
        print("Command recording finished.")
        wav_buffer = io.BytesIO()
        write(wav_buffer, samplerate, command_recording_np)
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
        transcribed_text = response.text.strip()
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

def publish_intent_external(topic, intent_name, confidence, slots=None):
    global intent_publisher_client
    if not intent_publisher_client or not intent_publisher_client.is_connected():
        print("Intent publishing MQTT client not connected. Cannot publish intent.", file=sys.stderr)
        return False
    message_dict = {"intent": intent_name, "confidence": confidence}
    if slots:
        message_dict["slots"] = slots
    message_json = json.dumps(message_dict)
    result = intent_publisher_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Intent published to EXTERNAL MQTT topic {topic}: {message_json}")
        return True
    else:
        print(f"Failed to send message to EXTERNAL topic {topic} (Error code: {status})")
        return False

# --- Wake Word and Command Handling ---
def process_command_after_wake():
    global is_processing_command
    print("\n--- Wake Word Confirmed! Processing Command ---")

    command_audio_data = record_command_audio(COMMAND_DURATION, SAMPLE_RATE, CHANNELS)

    if command_audio_data:
        text = get_text_from_audio(command_audio_data)
        if text:
            intent_result = get_intent_from_text(text)
            if intent_result and intent_result.get('intent') and intent_result['intent'].get('name'):
                intent_name = intent_result['intent']['name']
                confidence = intent_result['intent'].get('confidence', 0.0)
                slots = intent_result.get('slots', {})
                print("\n--- Recognized Intent ---")
                print(f"Intent: {intent_name}")
                print(f"Confidence: {confidence:.2f}")
                if slots: print(f"Slots: {slots}")
                print("-------------------------")
                publish_intent_external(EXTERNAL_MQTT_INTENT_TOPIC, intent_name, confidence, slots)
            else:
                print("Could not recognize a valid intent from text.")
        else:
            print("Could not transcribe audio to text.")
    else:
        print("Failed to record command audio.")

    with processing_lock:
        is_processing_command = False
    print(f"\nListening for wake word '{EXPECTED_WAKEWORD_ID}' via Rhasspy MQTT...")


# --- MQTT Callbacks (Rhasspy Wake Word Listener) ---
def on_connect_rhasspy_listener(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to Rhasspy MQTT Broker: {RHASSPY_MQTT_BROKER}")
        client.subscribe(RHASSPY_WAKE_WORD_TOPIC)
        print(f"Subscribed to Rhasspy wake word topic: {RHASSPY_WAKE_WORD_TOPIC}")
    else:
        print(f"Failed to connect to Rhasspy MQTT Broker, reason code {reason_code}")

def on_message_rhasspy_listener(client, userdata, msg):
    global is_processing_command
    print(f"\n--- MQTT Message Received from Rhasspy ---")
    print(f"Topic: {msg.topic}")
    try:
        payload_str = msg.payload.decode('utf-8')
        payload_json = json.loads(payload_str)
        print(f"Payload: {json.dumps(payload_json, indent=2)}")

        detected_wakeword_id = payload_json.get('wakewordId')
        site_id = payload_json.get('siteId', 'N/A') # Rhasspy usually includes siteId

        if detected_wakeword_id == EXPECTED_WAKEWORD_ID:
            print(f"Expected wake word '{EXPECTED_WAKEWORD_ID}' detected on site '{site_id}'!")
            with processing_lock:
                if is_processing_command:
                    print("Already processing a command, ignoring this wake word.")
                    return
                is_processing_command = True
            
            # Start command processing in a new thread to not block MQTT loop
            thread = threading.Thread(target=process_command_after_wake)
            thread.daemon = True
            thread.start()
        elif detected_wakeword_id:
            print(f"A wake word ('{detected_wakeword_id}') was detected, but not the one we're waiting for ('{EXPECTED_WAKEWORD_ID}').")
        else:
            print("Received message on wake word topic, but 'wakewordId' is missing in payload.")

    except json.JSONDecodeError:
        print(f"Could not decode Rhasspy MQTT payload as JSON: {msg.payload.decode('utf-8')}")
    except Exception as e:
        print(f"Error processing Rhasspy MQTT message: {e}")
    print("------------------------------------------")

# --- Main Execution ---
if __name__ == "__main__":
    try:
        # Initialize Intent Publishing MQTT Client
        intent_publisher_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="jarvis_intent_publisher")
        intent_publisher_client.on_connect = on_connect_intent_publisher
        intent_publisher_client.on_publish = on_publish_intent_publisher
        print(f"Connecting to Intent Publishing MQTT broker {EXTERNAL_MQTT_BROKER}...")
        intent_publisher_client.connect(EXTERNAL_MQTT_BROKER, EXTERNAL_MQTT_PORT, 60)
        intent_publisher_client.loop_start() # Start in a background thread

        # Initialize Rhasspy Wake Word Listener MQTT Client
        rhasspy_listener_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="jarvis_rhasspy_wake_listener")
        rhasspy_listener_client.on_connect = on_connect_rhasspy_listener
        rhasspy_listener_client.on_message = on_message_rhasspy_listener
        
        print(f"Connecting to Rhasspy MQTT broker {RHASSPY_MQTT_BROKER}...")
        rhasspy_listener_client.connect(RHASSPY_MQTT_BROKER, RHASSPY_MQTT_PORT, 60)
        
        # Give clients time to connect
        time.sleep(2) 
        if not intent_publisher_client.is_connected():
             print("Warning: Intent publisher client failed to connect. Intents will not be published.")
        if not rhasspy_listener_client.is_connected():
            raise ConnectionError("Failed to connect to Rhasspy MQTT broker. Cannot listen for wake words.")

        print(f"\nListening for wake word '{EXPECTED_WAKEWORD_ID}' via Rhasspy MQTT... Press Ctrl+C to stop.")
        rhasspy_listener_client.loop_forever() # Blocks here, listening for messages

    except ConnectionError as e:
         print(f"MQTT Connection Error: {e}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Stopping...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if rhasspy_listener_client:
            rhasspy_listener_client.loop_stop()
            rhasspy_listener_client.disconnect()
            print("Rhasspy listener MQTT client disconnected.")
        if intent_publisher_client:
            intent_publisher_client.loop_stop()
            intent_publisher_client.disconnect()
            print("Intent publisher MQTT client disconnected.")
        print("Script finished.")