import requests
import sys
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import io
import json
import paho.mqtt.client as mqtt
import time
import uuid

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent"

# External MQTT (for publishing results)
EXTERNAL_MQTT_BROKER = "localhost"
EXTERNAL_MQTT_PORT = 1883
EXTERNAL_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized"
CONTROL_TOPIC = "central_main/control"

# Recording parameters
SAMPLE_RATE = 16000  # Hz
COMMAND_DURATION = 5  # Seconds to record command
CHANNELS = 1        # mono

# --- MQTT Client ---
external_mqtt_client = None

# --- MQTT Callbacks (External Broker) ---
def on_connect_external(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to External MQTT Broker: {EXTERNAL_MQTT_BROKER}")
    else:
        print(f"Failed to connect to External MQTT Broker, reason code {reason_code}")

def on_publish_external(client, userdata, mid, reason_code, properties):
    pass

def on_log(client, userdata, level, buf):
    print(f"MQTT Log: {buf}")

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
    if not audio_data:
        return None
    print("Sending command audio to Rhasspy STT...")
    try:
        headers = {'Content-Type': 'audio/wav'}
        response = requests.post(STT_ENDPOINT, headers=headers, data=audio_data, timeout=20)
        print(f"STT request sent. Status code: {response.status_code}")
        response.raise_for_status()
        transcribed_text = response.text
        print(f"STT API Result (text): '{transcribed_text}'")
        return transcribed_text
    except requests.exceptions.ConnectionError as e:
        print(f"Error: Rhasspy STT server is not running or unreachable at {RHASSPY_URL}: {e}", file=sys.stderr)
        time.sleep(2)
        return None
    except Exception as e:
        print(f"Error during STT request: {e}", file=sys.stderr)
        time.sleep(2)
        return None

def get_intent_from_text(text):
    if not text:
        return None
    print(f"Sending text '{text}' to Rhasspy NLU...")
    try:
        response = requests.post(NLU_ENDPOINT, data=text.encode('utf-8'), timeout=10)
        print(f"NLU request sent. Status code: {response.status_code}")
        response.raise_for_status()
        intent_data = response.json()
        print(f"NLU API Result (JSON): {json.dumps(intent_data, indent=2)}")
        return intent_data
    except requests.exceptions.ConnectionError as e:
        print(f"Error: Rhasspy NLU server is not running or unreachable at {RHASSPY_URL}: {e}", file=sys.stderr)
        time.sleep(2)
        return None
    except Exception as e:
        print(f"Error during NLU request: {e}", file=sys.stderr)
        time.sleep(2)
        return None

def generate_control_token(intent_data):
    """Generate MQTT control token based on intent data."""
    intent_name = intent_data['intent'].get('name', '')
    slots = intent_data.get('slots', {})

    # Default token structure
    token = None

    # Door control (LOCK/UNLOCK)
    if intent_name == 'LockDoor':
        door_name = slots.get('door', 'Font Door')
        token = {"name": door_name, "state": "lock"}
    elif intent_name == 'UnlockDoor':
        door_name = slots.get('door', 'Font Door')
        token = {"name": door_name, "state": "unlock"}

    # Switch/Light control (ON/OFF)
    elif intent_name == 'TurnOnDevice':
        device_name = slots.get('device', 'LivingRoom L1')
        token = {"name": device_name, "state": "on"}
    elif intent_name == 'TurnOffDevice':
        device_name = slots.get('device', 'LivingRoom L1')
        token = {"name": device_name, "state": "off"}
    
    # Specific light control for Light1_On
    elif intent_name == 'Light1_On':
        token = {"name": "Light1", "state": "on"}

    # Batch mode control
    elif intent_name == 'BatchControl':
        control_type = slots.get('type', '').lower()
        state = slots.get('state', '').lower()
        if control_type == 'switches' and state in ['on', 'off']:
            token = {"name": "CMD_SWITCH_ALL", "state": state}
        elif control_type == 'lights' and state in ['on', 'off']:
            token = {"name": "CMD_LIGHT_ALL", "state": state}
        elif control_type == 'doors' and state in ['lock', 'unlock']:
            token = {"name": "CMD_DOOR_ALL", "state": state}

    return token

def publish_intent_external(topic, intent_name, confidence):
    global external_mqtt_client
    if not external_mqtt_client or not external_mqtt_client.is_connected():
        print("External MQTT client not connected. Cannot publish intent.", file=sys.stderr)
        return False
    message_dict = {"intent": intent_name, "confidence": confidence}
    message_json = json.dumps(message_dict)
    result = external_mqtt_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Intent published to EXTERNAL MQTT topic {topic}: {message_json}")
        return True
    else:
        print(f"Failed to send message to EXTERNAL topic {topic} (Error code: {status})")
        return False

def publish_control_token(topic, token):
    global external_mqtt_client
    if not external_mqtt_client or not external_mqtt_client.is_connected():
        print("External MQTT client not connected. Cannot publish control token.", file=sys.stderr)
        return False
    if not token:
        print("No valid control token to publish.", file=sys.stderr)
        return False
    message_json = json.dumps(token)
    result = external_mqtt_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Control token published to MQTT topic {topic}: {message_json}")
        return True
    else:
        print(f"Failed to send control token to topic {topic} (Error code: {status})")
        return False

def connect_mqtt_with_retry(client, broker, port, max_attempts=3, delay=5):
    attempt = 1
    while attempt <= max_attempts:
        try:
            print(f"Attempt {attempt}/{max_attempts}: Connecting to MQTT broker {broker}...")
            client.connect(broker, port, 60)
            client.loop_start()
            for _ in range(6):  # Wait up to 6 seconds, checking every second
                if client.is_connected():
                    print(f"Successfully connected to {broker}")
                    return True
                time.sleep(1)
            print("Connection established but not active after 6 seconds.")
        except Exception as e:
            print(f"Connection attempt {attempt} failed: {str(e)}")
        client.loop_stop()
        time.sleep(delay)
        attempt += 1
    return False

# --- Main Execution ---
if __name__ == "__main__":
    # Initialize External MQTT Client
    external_mqtt_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"voice_control_{str(uuid.uuid4())}",
        protocol=mqtt.MQTTv311
    )
    external_mqtt_client.on_connect = on_connect_external
    external_mqtt_client.on_publish = on_publish_external
    external_mqtt_client.on_log = on_log

    try:
        # Connect to External Broker
        if not connect_mqtt_with_retry(external_mqtt_client, EXTERNAL_MQTT_BROKER, EXTERNAL_MQTT_PORT):
            raise ConnectionError("Failed to connect to external MQTT broker after multiple attempts.")

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

                        # 4. Publish original intent
                        publish_intent_external(EXTERNAL_MQTT_INTENT_TOPIC, intent_name, confidence)

                        # 5. Generate and publish control token
                        control_token = generate_control_token(intent_result)
                        if control_token:
                            publish_control_token(CONTROL_TOPIC, control_token)
                        else:
                            print("No control token generated for this intent.")
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
            except Exception:
                pass
            print("\nExternal MQTT client stopped (was not connected or loop not started).")

        print("Script finished.")