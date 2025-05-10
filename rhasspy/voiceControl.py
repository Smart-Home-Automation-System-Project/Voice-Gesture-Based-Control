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

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent"

# External MQTT (for publishing results)
EXTERNAL_MQTT_BROKER = "broker.hivemq.com"   #test.mosquitto.org #localhost
EXTERNAL_MQTT_PORT = 1883
EXTERNAL_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized"

# Recording parameters
SAMPLE_RATE = 16000  # Hz
COMMAND_DURATION = 5 # Seconds to record command
CHANNELS = 1       # mono

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

def publish_intent_external(topic, intent_name, confidence):
    global external_mqtt_client
    if not external_mqtt_client or not external_mqtt_client.is_connected():
        print("External MQTT client not connected. Cannot publish intent.", file=sys.stderr)
        return False # Indicate failure
    message_dict = {"intent": intent_name, "confidence": confidence}
    message_json = json.dumps(message_dict)
    result = external_mqtt_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Intent published to EXTERNAL MQTT topic {topic}: {message_json}")
        return True # Indicate success
    else:
        print(f"Failed to send message to EXTERNAL topic {topic} (Error code: {status})")
        return False # Indicate failure

# --- Main Execution ---
if __name__ == "__main__":
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
                        confidence = intent_result['intent'].get('confidence', 'N/A')
                        print("\n--- Recognized Intent ---")
                        print(f"Intent: {intent_name}")
                        print(f"Confidence: {confidence}")
                        print("-------------------------")

                        # 4. Publish to external MQTT
                        publish_intent_external(EXTERNAL_MQTT_INTENT_TOPIC, intent_name, confidence)
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
        print("\nCtrl+C detected. Stopping continuous loop...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        if external_mqtt_client and external_mqtt_client.is_connected():
            external_mqtt_client.loop_stop()
            external_mqtt_client.disconnect()
            print("\nExternal MQTT client stopped and disconnected.")
        elif external_mqtt_client:
             try:
                 external_mqtt_client.disconnect()
             except Exception: pass
             print("\nExternal MQTT client stopped (was not connected or loop not started).")

        print("Script finished.")