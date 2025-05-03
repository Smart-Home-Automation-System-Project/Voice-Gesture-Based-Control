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
RHASSPY_MQTT_HOST = "localhost"
RHASSPY_MQTT_PORT = 1883 # *** Make sure this matches your Rhasspy MQTT setting ***
WAKE_WORD_TOPIC = "hermes/hotword/+/detected" # Listen for wake word detection

# External MQTT (for publishing results)
EXTERNAL_MQTT_BROKER = "test.mosquitto.org"
EXTERNAL_MQTT_PORT = 1883
EXTERNAL_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized"

# Recording parameters
SAMPLE_RATE = 16000  # Hz
COMMAND_DURATION = 5 # Seconds to record command after wake word
CHANNELS = 1       # mono
RECORDING_FILENAME = "last_command_recording.wav"

# --- State ---
is_processing = False # Flag to prevent processing multiple commands at once
processing_lock = threading.Lock()

# --- MQTT Clients ---
rhasspy_mqtt_client = None
external_mqtt_client = None

# --- MQTT Callbacks (Rhasspy Internal) ---
def on_connect_rhasspy(client, userdata, flags, reason_code, properties):
    """Callback when connected to Rhasspy's MQTT broker."""
    if reason_code == 0:
        print(f"Connected to Rhasspy MQTT ({RHASSPY_MQTT_HOST}:{RHASSPY_MQTT_PORT})")
        client.subscribe(WAKE_WORD_TOPIC)
        print(f"Subscribed to Rhasspy wake word topic: {WAKE_WORD_TOPIC}")
    else:
        print(f"Failed to connect to Rhasspy MQTT, reason code {reason_code}", file=sys.stderr)

def on_message_rhasspy(client, userdata, msg):
    """Callback when a message is received from Rhasspy's MQTT."""
    global is_processing
    if msg.topic.startswith("hermes/hotword/") and msg.topic.endswith("/detected"):
        with processing_lock:
            if is_processing:
                print("Wake word detected, but already processing a command. Ignoring.")
                return # Already busy
            # Set flag immediately to prevent race conditions
            is_processing = True

        print("-" * 20)
        print(f"Wake word detected on topic: {msg.topic}")
        # payload = json.loads(msg.payload.decode('utf-8')) # Optional: inspect payload
        # print(f"Wake word payload: {payload}")

        # Trigger the command processing in a separate thread
        # to avoid blocking the MQTT loop
        thread = threading.Thread(target=handle_command_after_wake)
        thread.start()
        print("Started command handling thread.")
        print("-" * 20)

# --- MQTT Callbacks (External Broker) ---
def on_connect_external(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to External MQTT Broker: {EXTERNAL_MQTT_BROKER}")
    else:
        print(f"Failed to connect to External MQTT Broker, reason code {reason_code}")

def on_publish_external(client, userdata, mid, reason_code, properties):
    # print(f"External message {mid} published (Reason Code: {reason_code})")
    pass

# --- Audio & Processing Functions ---
# (These are mostly copied from getIntentMQTT.py)
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
        print(f"STT request sent. Status code: {response.status_code}")
        response.raise_for_status()
        transcribed_text = response.text
        print(f"STT API Result (text): '{transcribed_text}'")
        return transcribed_text
    except Exception as e:
        print(f"Error during STT request: {e}", file=sys.stderr)
        return None

def get_intent_from_text(text):
    if not text: return None
    print(f"Sending text '{text}' to Rhasspy NLU...")
    try:
        response = requests.post(NLU_ENDPOINT, data=text.encode('utf-8'), timeout=10)
        print(f"NLU request sent. Status code: {response.status_code}")
        response.raise_for_status()
        intent_data = response.json()
        print(f"NLU API Result (JSON): {json.dumps(intent_data, indent=2)}")
        return intent_data
    except Exception as e:
        print(f"Error during NLU request: {e}", file=sys.stderr)
        return None

def publish_intent_external(topic, intent_name, confidence):
    global external_mqtt_client
    if not external_mqtt_client or not external_mqtt_client.is_connected():
        print("External MQTT client not connected. Cannot publish intent.", file=sys.stderr)
        return
    message_dict = {"intent": intent_name, "confidence": confidence}
    message_json = json.dumps(message_dict)
    result = external_mqtt_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Intent published to EXTERNAL MQTT topic {topic}: {message_json}")
    else:
        print(f"Failed to send message to EXTERNAL topic {topic} (Error code: {status})")

# --- Command Handling Logic ---
def handle_command_after_wake():
    """Records audio, gets intent, publishes, then resets processing flag."""
    global is_processing
    try:
        # 1. Record command audio
        command_audio = record_audio(COMMAND_DURATION, SAMPLE_RATE, CHANNELS)

        if command_audio:
            # Optional: Save recording
            try:
                with open(RECORDING_FILENAME, "wb") as f: f.write(command_audio)
                print(f"Command recording saved to {RECORDING_FILENAME}")
            except Exception as e_write: print(f"Error saving recording: {e_write}", file=sys.stderr)

            # 2. Get text
            text = get_text_from_audio(command_audio)

            if text:
                # 3. Get intent
                intent_result = get_intent_from_text(text)

                if intent_result and intent_result.get('intent'):
                    intent_name = intent_result['intent'].get('name', 'UnknownIntent')
                    confidence = intent_result['intent'].get('confidence', 'N/A')
                    print("\n--- Recognized Intent ---")
                    print(f"Intent: {intent_name}")
                    print(f"Confidence: {confidence}")
                    print("-------------------------")

                    # 4. Publish to external MQTT
                    publish_intent_external(EXTERNAL_MQTT_INTENT_TOPIC, intent_name, confidence)
                else:
                    print("Could not recognize intent from text.", file=sys.stderr)
            else:
                print("Could not transcribe audio.", file=sys.stderr)
        else:
            print("Failed to record command audio.", file=sys.stderr)

    except Exception as e:
        print(f"An error occurred in handle_command_after_wake: {e}", file=sys.stderr)
    finally:
        # IMPORTANT: Reset the flag so we can detect the wake word again
        with processing_lock:
            is_processing = False
        print("Ready for next wake word.")

# --- Main Execution ---
if __name__ == "__main__":
    # Initialize Rhasspy MQTT Client
    rhasspy_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    rhasspy_mqtt_client.on_connect = on_connect_rhasspy
    rhasspy_mqtt_client.on_message = on_message_rhasspy

    # Initialize External MQTT Client
    external_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    external_mqtt_client.on_connect = on_connect_external
    external_mqtt_client.on_publish = on_publish_external

    try:
        # Connect to External Broker
        print(f"Connecting to External MQTT broker {EXTERNAL_MQTT_BROKER}...")
        external_mqtt_client.connect(EXTERNAL_MQTT_BROKER, EXTERNAL_MQTT_PORT, 60)
        external_mqtt_client.loop_start() # Start background thread

        # Connect to Rhasspy Broker
        print(f"Connecting to Rhasspy MQTT broker {RHASSPY_MQTT_HOST}...")
        rhasspy_mqtt_client.connect(RHASSPY_MQTT_HOST, RHASSPY_MQTT_PORT, 60)

        # Start the Rhasspy MQTT loop (this runs forever until interrupted)
        print("Listening for wake word via Rhasspy MQTT...")
        rhasspy_mqtt_client.loop_forever()

    except ConnectionRefusedError as e:
        print(f"MQTT Connection Refused: {e}. Check broker address/port and if Rhasspy/broker is running.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nStopping script...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        if rhasspy_mqtt_client and rhasspy_mqtt_client.is_connected():
            rhasspy_mqtt_client.loop_stop()
            rhasspy_mqtt_client.disconnect()
            print("Rhasspy MQTT client stopped and disconnected.")
        if external_mqtt_client and external_mqtt_client.is_connected():
            external_mqtt_client.loop_stop()
            external_mqtt_client.disconnect()
            print("External MQTT client stopped and disconnected.")
        print("Script finished.")