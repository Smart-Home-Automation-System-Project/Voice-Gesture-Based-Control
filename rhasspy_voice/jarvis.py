#still in 0.9.9 version. not stable yet
import sys
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import io
import json
import requests
import paho.mqtt.client as mqtt
import time
import threading
from pocketsphinx import LiveSpeech, get_model_path

# Import the new parser function
from rhasspy_voice.intent_parser import parse_rhasspy_intent

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent"

EXTERNAL_MQTT_BROKER = "mqtt.local"
EXTERNAL_MQTT_PORT = 1883
EXTERNAL_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized"

SAMPLE_RATE = 16000
CHANNELS = 1
COMMAND_DURATION = 5
WAKE_WORD = "jarvis"
POCKETSPHINX_THRESHOLD = 1e-42

# --- Global State ---
is_processing_command = False
processing_lock = threading.Lock()
intent_publisher_client = None

# --- MQTT Callbacks ---
def on_connect_intent_publisher(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to Intent Publishing MQTT Broker: {EXTERNAL_MQTT_BROKER}")
    else:
        print(f"Failed to connect to Intent Publishing MQTT Broker, reason code {reason_code}")

def on_publish_intent_publisher(client, userdata, mid, reason_code, properties):
    pass

# --- Audio & Processing Functions ---
def record_command_audio(duration, samplerate, channels):
    print(f"Listening for command ({duration} seconds)...")
    try:
        command_recording_np = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
        sd.wait()
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

# Modified to accept a payload dictionary
def publish_intent_external(topic, payload_dict):
    global intent_publisher_client
    if not intent_publisher_client or not intent_publisher_client.is_connected():
        print("Intent publishing MQTT client not connected.", file=sys.stderr)
        return False
    
    message_json = json.dumps(payload_dict) # Convert the dictionary to a JSON string
    
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
    print("\n--- Wake Word Confirmed by LiveSpeech! Processing Command ---")

    command_audio_data = record_command_audio(COMMAND_DURATION, SAMPLE_RATE, CHANNELS)

    if command_audio_data:
        text = get_text_from_audio(command_audio_data)
        if text:
            intent_result = get_intent_from_text(text)
            if intent_result and intent_result.get('intent') and intent_result['intent'].get('name'):
                intent_name = intent_result['intent']['name']
                # confidence = intent_result['intent'].get('confidence', 0.0) # Available if needed
                # slots = intent_result.get('slots', {}) # Available if needed

                print("\n--- Recognized Intent (Raw from Rhasspy) ---")
                print(f"Intent: {intent_name}")
                print(f"Confidence: {intent_result['intent'].get('confidence', 'N/A')}")
                print("------------------------------------------")

                # Parse the Rhasspy intent to your custom format
                custom_payload = parse_rhasspy_intent(intent_name)

                if custom_payload:
                    # Publish the new custom payload
                    publish_intent_external(EXTERNAL_MQTT_INTENT_TOPIC, custom_payload)
                else:
                    print(f"Intent '{intent_name}' not mapped to custom payload. Not publishing.")
            else:
                print("Could not recognize a valid intent from text.")
        else:
            print("Could not transcribe audio to text.")
    else:
        print("Failed to record command audio.")

    with processing_lock:
        is_processing_command = False
    print(f"\nListening for wake word '{WAKE_WORD}' with LiveSpeech...")

# --- Main Execution ---
def main_loop():
    global is_processing_command, intent_publisher_client

    try:
        intent_publisher_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="jarvis_intent_publisher_ps_custom")
        intent_publisher_client.on_connect = on_connect_intent_publisher
        intent_publisher_client.on_publish = on_publish_intent_publisher
        print(f"Connecting to Intent Publishing MQTT broker {EXTERNAL_MQTT_BROKER}...")
        intent_publisher_client.connect(EXTERNAL_MQTT_BROKER, EXTERNAL_MQTT_PORT, 60)
        intent_publisher_client.loop_start()
        time.sleep(1)
        if not intent_publisher_client.is_connected():
            print(f"Warning: Intent publisher client failed to connect to {EXTERNAL_MQTT_BROKER}.")

        print(f"\nListening for wake word '{WAKE_WORD}' with LiveSpeech (Threshold: {POCKETSPHINX_THRESHOLD})... Press Ctrl+C to stop.")

        # Ensure LiveSpeech uses the correct sample rate if it's not default
        # LiveSpeech defaults to 16000, which matches our SAMPLE_RATE
        speech = LiveSpeech(
            verbose=False,
            sampling_rate=SAMPLE_RATE, # Explicitly set, though default is 16000
            buffer_size=2048,
            no_search=False,
            full_utt=False,
            hmm=get_model_path('en-us'),
            lm=None, # Using keyphrase spotting, so no language model needed here
            dic=get_model_path('cmudict-en-us.dict'),
            keyphrase=WAKE_WORD,
            kws_threshold=POCKETSPHINX_THRESHOLD
        )

        for phrase in speech:
            # phrase object contains segments, we are interested in the text
            detected_text = str(phrase).strip().lower()
            # LiveSpeech with keyphrase might sometimes yield the phrase itself or parts of it.
            # We confirm if our WAKE_WORD is in what's detected.
            if WAKE_WORD in detected_text:
                print(f"Wake word '{WAKE_WORD}' detected by LiveSpeech: {detected_text}")
                with processing_lock:
                    if is_processing_command:
                        continue
                    is_processing_command = True

                thread = threading.Thread(target=process_command_after_wake)
                thread.daemon = True
                thread.start()
            # else: # Optional: print if something else was transcribed by LiveSpeech
            #     print(f"LiveSpeech transcribed (no wake word): {detected_text}")


    except KeyboardInterrupt:
        print("\nCtrl+C detected. Stopping...")
    except Exception as e:
        print(f"An unexpected error occurred in main_loop: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if intent_publisher_client and intent_publisher_client.is_connected():
            intent_publisher_client.loop_stop()
            intent_publisher_client.disconnect()
            print("Intent publisher MQTT client disconnected.")
        print("Script finished.")

if __name__ == "__main__":
    # Ensure intent_parser.py is in the same directory or Python's path
    main_loop()