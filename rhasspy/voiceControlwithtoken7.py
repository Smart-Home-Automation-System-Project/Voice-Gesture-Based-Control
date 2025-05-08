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

# Device list (id, name, type)
DEVICES = [
    ("L-2025.04.19-21.09-0001", "l1", "light"),
    ("L-2025.04.19-21.09-0002", "l2", "light"),
    ("L-2025.04.19-21.09-0003", "l3", "light"),
    ("L-2025.04.19-21.09-0004", "l4", "light"),
    ("L-2025.04.19-21.09-0005", "l5", "light"),
    ("L-2025.04.19-21.09-0006", "l6", "light"),
    ("L-2025.04.19-21.09-0007", "l7", "light"),
    ("L-2025.04.19-21.09-0008", "l8", "light"),
    ("T-2025.04.19-21.09-0001", "t1", "temp"),
    ("T-2025.04.19-21.09-0002", "t2", "temp"),
    ("T-2025.04.19-21.09-0003", "t3", "temp"),
    ("T-2025.04.19-21.09-0004", "t4", "temp"),
    ("R-2025.04.19-21.09-0001", "r1", "radar"),
    ("R-2025.04.19-21.09-0002", "r2", "radar"),
    ("R-2025.04.19-21.09-0003", "r3", "radar"),
    ("R-2025.04.19-21.09-0004", "r4", "radar"),
    ("R-2025.04.19-21.09-0005", "r5", "radar"),
    ("R-2025.04.19-21.09-0006", "r6", "radar"),
    ("R-2025.04.19-21.09-0007", "r7", "radar"),
    ("R-2025.04.19-21.09-0008", "r8", "radar"),
    ("D-2025.04.19-21.09-0001", "front door", "door"),
    ("SW-2025.04.19-21.09-0001", "living room tv", "switch")
]

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

def generate_control_message(intent_data):
    """Generate MQTT control message based on intent data."""
    intent_name = intent_data['intent'].get('name', '')
    slots = intent_data.get('slots', {})

    # Default message structure (array)
    messages = []

    # Helper function to find device details by name
    def find_device_details(device_name):
        device_name = device_name.lower()
        for device_id, name, device_type in DEVICES:
            if name.lower() == device_name:
                return {"category": device_type, "client_id": device_id, "name": name}
        return None

    # Device control (ON/OFF)
    if intent_name == 'TurnOnDevice':
        device_name = slots.get('device', '')
        device_details = find_device_details(device_name)
        if device_details:
            device_details["state"] = "on"
            messages.append(device_details)
    elif intent_name == 'TurnOffDevice':
        device_name = slots.get('device', '')
        device_details = find_device_details(device_name)
        if device_details:
            device_details["state"] = "off"
            messages.append(device_details)

    # Door control (LOCK/UNLOCK)
    elif intent_name == 'LockDoor':
        device_name = slots.get('device', 'front door')
        device_details = find_device_details(device_name)
        if device_details:
            device_details["state"] = "lock"
            messages.append(device_details)
    elif intent_name == 'UnlockDoor':
        device_name = slots.get('device', 'front door')
        device_details = find_device_details(device_name)
        if device_details:
            device_details["state"] = "unlock"
            messages.append(device_details)

    # Backward compatibility for Light1_On (if still in Rhasspy config)
    elif intent_name == 'Light1_On':
        device_details = find_device_details('l1')
        if device_details:
            device_details["state"] = "on"
            messages.append(device_details)

    # Batch mode control
    elif intent_name == 'BatchControl':
        control_type = slots.get('type', '').lower()
        state = slots.get('state', '').lower()
        if control_type in ['lights', 'switches', 'doors'] and state in ['on', 'off', 'lock', 'unlock']:
            target_type = 'light' if control_type == 'lights' else 'switch' if control_type == 'switches' else 'door'
            for device_id, name, device_type in DEVICES:
                if device_type == target_type:
                    messages.append({
                        "category": device_type,
                        "client_id": device_id,
                        "name": name,
                        "state": state
                    })

    return messages

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

def publish_control_message(topic, messages):
    global external_mqtt_client
    if not external_mqtt_client or not external_mqtt_client.is_connected():
        print("External MQTT client not connected. Cannot publish control message.", file=sys.stderr)
        return False
    if not messages:
        print("No valid control message to publish.", file=sys.stderr)
        return False
    message_json = json.dumps(messages)
    result = external_mqtt_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Control message published to MQTT topic {topic}: {message_json}")
        return True
    else:
        print(f"Failed to send control message to topic {topic} (Error code: {status})")
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

                        # 5. Generate and publish control message
                        control_messages = generate_control_message(intent_result)
                        if control_messages:
                            publish_control_message(CONTROL_TOPIC, control_messages)
                        else:
                            print("No control message generated for this intent.")
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



'''
expected output :

Listening for command (5 seconds)...
Command recording finished.
Sending command audio to Rhasspy STT...
STT request sent. Status code: 200
STT API Result (text): 'turn on l1'
Sending text 'turn on l1' to Rhasspy NLU...
NLU request sent. Status code: 200
NLU API Result (JSON): {
  "intent": {
    "name": "TurnOnDevice",
    "confidence": 1.0
  },
  "slots": {
    "device": "l1"
  },
  ...
}
--- Recognized Intent ---
Intent: TurnOnDevice
Confidence: 1.0
-------------------------
Intent published to EXTERNAL MQTT topic rhasspy/intent/recognized: {"intent": "TurnOnDevice", "confidence": 1.0}
Control message published to MQTT topic central_main/control: [{"category": "light", "client_id": "L-2025.04.19-21.09-0001", "name": "l1", "state": "on"}]

'''