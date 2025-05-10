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

# Import the new parser function
from intent_parser import parse_rhasspy_intent

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent"

# External MQTT (for publishing results)
EXTERNAL_MQTT_BROKER = "broker.localhost" #"test.mosquitto.org" #"localhost"
EXTERNAL_MQTT_PORT = 1883
EXTERNAL_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized"

# Recording parameters
SAMPLE_RATE = 44100#16000  # Hz
COMMAND_DURATION = 5 # Seconds to record command
CHANNELS = 1       # mono
INPUT_DEVICE_ID = 0 # <--- ADD THIS LINE (Use the device ID for your microphone)

# --- MQTT Client ---
external_mqtt_client = None

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
def record_audio(duration, samplerate, channels):
    # Use the globally defined INPUT_DEVICE_ID
    print(f"Listening for command ({duration} seconds) on device ID {INPUT_DEVICE_ID}...")
    try:
        # Pass the device ID to sd.rec()
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16', device=INPUT_DEVICE_ID)
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
        time.sleep(2)
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
        time.sleep(2)
        return None

# Modified to accept a payload dictionary
def publish_intent_external(topic, payload_dict):
    global external_mqtt_client
    if not external_mqtt_client or not external_mqtt_client.is_connected():
        print("External MQTT client not connected. Cannot publish intent.", file=sys.stderr)
        return False # Indicate failure
    
    message_json = json.dumps(payload_dict) # Convert the dictionary to a JSON string
    
    result = external_mqtt_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Intent published to EXTERNAL MQTT topic {topic}: {message_json}")
        return True # Indicate success
    else:
        print(f"Failed to send message to EXTERNAL topic {topic} (Error code: {status})")
        return False # Indicate failure

# --- Main Execution ---
# Encapsulate the main logic into a function
def run_voice_control_system():
    global external_mqtt_client # Ensure we're using the global client

    # Initialize External MQTT Client
    external_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    external_mqtt_client.on_connect = on_connect_external
    external_mqtt_client.on_publish = on_publish_external

    try:
        # Connect to External Broker
        print(f"Connecting to External MQTT broker {EXTERNAL_MQTT_BROKER}...")
        external_mqtt_client.connect(EXTERNAL_MQTT_BROKER, EXTERNAL_MQTT_PORT, 60)
        external_mqtt_client.loop_start() # Start background thread
        # Wait briefly for connection to establish
        time.sleep(1)
        if not external_mqtt_client.is_connected():
             raise ConnectionError("Failed to connect to external MQTT broker.")

        # --- Continuous Loop ---
        print("\nStarting continuous voice control loop (Press Ctrl+C to stop)...")
        while True:
            print("-" * 30)
            # 1. Record command audio
            command_audio = record_audio(COMMAND_DURATION, SAMPLE_RATE, CHANNELS)

            if command_audio:
                # 2. Get text
                text = get_text_from_audio(command_audio)

                if text:
                    # 3. Get intent
                    intent_result = get_intent_from_text(text)

                    if intent_result and intent_result.get('intent'):
                        intent_name = intent_result['intent'].get('name', 'UnknownIntent')
                        # Confidence is available in intent_result['intent'].get('confidence')
                        # but not used in the new payload format as per your example.

                        print("\n--- Recognized Intent (Raw from Rhasspy) ---")
                        print(f"Intent: {intent_name}")
                        print(f"Confidence: {intent_result['intent'].get('confidence', 'N/A')}")
                        print("------------------------------------------")

                        # 4. Parse the Rhasspy intent to your custom format
                        custom_payload = parse_rhasspy_intent(intent_name)

                        if custom_payload:
                            # 5. Publish the new custom payload
                            publish_intent_external(EXTERNAL_MQTT_INTENT_TOPIC, custom_payload)
                        else:
                            # If parse_rhasspy_intent returned None, it means the intent
                            # was not mapped in intent_parser.py.
                            # You can decide to log this, do nothing, or publish a default/error.
                            print(f"Intent '{intent_name}' not mapped to custom payload. Not publishing.")
                    else:
                        print("Could not recognize intent from text.")
                else:
                    print("Could not transcribe audio.")
            else:
                print("Failed to record command audio. Retrying...")
                time.sleep(1)

    except ConnectionError as e:
         print(f"MQTT Connection Error: {e}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Stopping voice control loop...")
    except Exception as e:
        print(f"An unexpected error occurred in voice control: {e}", file=sys.stderr)
    finally:
        if external_mqtt_client and external_mqtt_client.is_connected():
            external_mqtt_client.loop_stop()
            external_mqtt_client.disconnect()
            print("\nVoice control external MQTT client stopped and disconnected.")
        elif external_mqtt_client:
             try:
                 external_mqtt_client.disconnect()
             except Exception: pass
             print("\nVoice control external MQTT client stopped (was not connected or loop not started).")

        print("Voice control script finished.")


if __name__ == "__main__":
    run_voice_control_system()