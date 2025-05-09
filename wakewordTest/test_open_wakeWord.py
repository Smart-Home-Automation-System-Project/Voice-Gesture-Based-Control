import requests
import sys
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import io
import json
import os
import paho.mqtt.client as mqtt # Still used for publishing final intent
import time
import threading
import collections

# Attempt to import OpenWakeWord
try:
    import openwakeword
except ImportError:
    print("OpenWakeWord library not found. Please install it: pip install openwakeword", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent"

# MQTT (for publishing final recognized intents)
EXTERNAL_MQTT_BROKER = "localhost"
EXTERNAL_MQTT_PORT = 1883
EXTERNAL_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized" # Or your preferred topic

# Audio Recording parameters
SAMPLE_RATE = 16000  # Hz (OpenWakeWord expects 16kHz)
CHANNELS = 1       # mono
COMMAND_DURATION = 5 # Seconds to record command AFTER wake word
AUDIO_CHUNK_SIZE = 1280  # Samples for OpenWakeWord (e.g., 80ms at 16kHz)

# OpenWakeWord settings
# Replace "hey_jarvis" with the actual model name you want to use from OpenWakeWord's pre-trained models
# or provide a path to your custom .tflite model.
# Common pre-trained models: "alexa", "hey_mycroft", "timer", "noise" etc.
# Check OpenWakeWord documentation for available pre-trained model names.
# If you trained a custom "jarvis.tflite" model for OpenWakeWord, use its path.
WAKE_WORD_MODEL_NAME = "hey_mycroft" # EXAMPLE! Change to your desired OpenWakeWord model
# Or if you have a custom .tflite model for OpenWakeWord:
# WAKE_WORD_MODEL_PATH = "/path/to/your/jarvis_openwakeword_model.tflite" 

# --- Global State ---
is_processing_command = False
processing_lock = threading.Lock()
oww_model = None # Will be initialized in main

# --- MQTT Client (for publishing intents) ---
intent_publisher_client = None

# --- MQTT Callbacks (Intent Publisher) ---
def on_connect_intent_publisher(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to Intent Publishing MQTT Broker: {EXTERNAL_MQTT_BROKER}")
    else:
        print(f"Failed to connect to Intent Publishing MQTT Broker, reason code {reason_code}")

def on_publish_intent_publisher(client, userdata, mid, reason_code, properties):
    pass # Keep it quiet

# --- Audio & Processing Functions (These remain largely the same) ---
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
    print("\n--- Wake Word Confirmed by OpenWakeWord! Processing Command ---")

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
    # After processing, go back to listening for the wake word
    print(f"\nListening for wake word '{WAKE_WORD_MODEL_NAME}' with OpenWakeWord...")


# --- Main Execution ---
def main_loop():
    global is_processing_command, oww_model

    # Audio input stream
    def audio_callback(indata, frames, time, status):
        global is_processing_command
        if status:
            print(f"Audio callback status: {status}", file=sys.stderr)
        
        with processing_lock:
            if is_processing_command:
                return # Don't process audio for wake word if already handling a command

        # Feed audio to OpenWakeWord
        # oww_model.predict() expects a NumPy array of 16-bit PCM audio
        prediction = oww_model.predict(indata[:,0]) # Assuming mono, take first channel

        # Check for wake word activation (scores are typically > 0.5 for activation)
        # The key in 'prediction' will be your WAKE_WORD_MODEL_NAME or the name embedded in your custom model
        if WAKE_WORD_MODEL_NAME in prediction and prediction[WAKE_WORD_MODEL_NAME] > 0.5: # Adjust threshold if needed
            print(f"Wake word '{WAKE_WORD_MODEL_NAME}' detected by OpenWakeWord with score: {prediction[WAKE_WORD_MODEL_NAME]:.2f}!")
            with processing_lock:
                if is_processing_command: # Double check
                    return
                is_processing_command = True
            
            # Stop the audio stream temporarily or handle in a way that doesn't conflict
            # For simplicity here, we'll let process_command_after_wake handle recording separately.
            # A more robust solution might pause this stream.
            
            # Start command processing in a new thread
            thread = threading.Thread(target=process_command_after_wake)
            thread.daemon = True
            thread.start()

    try:
        # Initialize OpenWakeWord Model
        print("Initializing OpenWakeWord...")
        # If using a pre-trained model name:
        oww_model = openwakeword.Model(wakeword_models=[WAKE_WORD_MODEL_NAME])
        # Or if using a custom model path:
        # oww_model = openwakeword.Model(custom_model_paths=[WAKE_WORD_MODEL_PATH])
        print("OpenWakeWord initialized.")

        # Initialize Intent Publishing MQTT Client
        global intent_publisher_client
        intent_publisher_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="jarvis_intent_publisher_direct_wake")
        intent_publisher_client.on_connect = on_connect_intent_publisher
        intent_publisher_client.on_publish = on_publish_intent_publisher
        print(f"Connecting to Intent Publishing MQTT broker {EXTERNAL_MQTT_BROKER}...")
        intent_publisher_client.connect(EXTERNAL_MQTT_BROKER, EXTERNAL_MQTT_PORT, 60)
        intent_publisher_client.loop_start() # Start in a background thread
        time.sleep(1)
        if not intent_publisher_client.is_connected():
             print(f"Warning: Intent publisher client failed to connect to {EXTERNAL_MQTT_BROKER}. Intents will not be published.")


        print(f"\nListening for wake word '{WAKE_WORD_MODEL_NAME}' with OpenWakeWord... Press Ctrl+C to stop.")
        # Start listening to the microphone with sounddevice
        with sd.InputStream(samplerate=SAMPLE_RATE, 
                             channels=CHANNELS, 
                             dtype='int16', 
                             blocksize=AUDIO_CHUNK_SIZE, # Process audio in chunks
                             callback=audio_callback):
            while True:
                time.sleep(0.1) # Keep the main thread alive

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
    main_loop()