import cv2
import mediapipe as mp
import numpy as np
import time
import math
import json
import paho.mqtt.client as mqtt
import requests
import sys
import sounddevice as sd
from scipy.io.wavfile import write
import io
import os
import threading
from intent_parser import parse_rhasspy_intent

# --- Configuration ---
# Gesture MQTT Configuration
GESTURE_MQTT_BROKER = "mqtt.localhost"
GESTURE_MQTT_PORT = 1883
GESTURE_MQTT_TOPIC = "central_main/control"
DOOR_NAME = "Front Door"

# Voice MQTT Configuration
VOICE_MQTT_BROKER = "broker.localhost"
VOICE_MQTT_PORT = 1883
VOICE_MQTT_INTENT_TOPIC = "rhasspy/intent/recognized"

# Rhasspy Configuration
RHASSPY_URL = "http://localhost:12101"
STT_ENDPOINT = f"{RHASSPY_URL}/api/speech-to-text"
NLU_ENDPOINT = f"{RHASSPY_URL}/api/text-to-intent"

# Voice Recording Parameters
SAMPLE_RATE = 16000  # Hz
COMMAND_DURATION = 5  # Seconds
CHANNELS = 1  # Mono

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# --- Gesture MQTT Client and Callbacks ---
def on_connect_gesture(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to Gesture MQTT Broker!")
    else:
        print(f"Failed to connect to Gesture MQTT, return code {rc}")

def on_publish_gesture(client, userdata, mid, properties=None):
    print(f"Gesture message {mid} published")

gesture_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
gesture_client.on_connect = on_connect_gesture
gesture_client.on_publish = on_publish_gesture
gesture_client.connect(GESTURE_MQTT_BROKER, GESTURE_MQTT_PORT)
gesture_client.loop_start()

# --- Voice MQTT Client and Callbacks ---
def on_connect_voice(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to Voice MQTT Broker: {VOICE_MQTT_BROKER}")
    else:
        print(f"Failed to connect to Voice MQTT Broker, reason code {reason_code}")

def on_publish_voice(client, userdata, mid, reason_code, properties):
    pass  # Silent to reduce console clutter

voice_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
voice_mqtt_client.on_connect = on_connect_voice
voice_mqtt_client.on_publish = on_publish_voice
voice_mqtt_client.connect(VOICE_MQTT_BROKER, VOICE_MQTT_PORT, 60)
voice_mqtt_client.loop_start()

# --- MQTT Publish Functions ---
def publish_gesture_message(topic, message_dict):
    message_json = json.dumps(message_dict)
    result = gesture_client.publish(topic, message_json)
    status = result[0]
    if status == 0:
        print(f"Gesture message sent to topic {topic}: {message_json}")
    else:
        print(f"Failed to send gesture message to topic {topic}")

def publish_voice_intent(topic, payload_dict):
    if not voice_mqtt_client.is_connected():
        print("Voice MQTT client not connected. Cannot publish intent.", file=sys.stderr)
        return False
    message_json = json.dumps(payload_dict)
    result = voice_mqtt_client.publish(topic, message_json)
    status = result.rc
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Voice intent published to topic {topic}: {message_json}")
        return True
    else:
        print(f"Failed to send voice message to topic {topic} (Error code: {status})")
        return False

# --- Gesture Detection Functions ---
def calculate_distance(point1, point2):
    return math.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)

def is_thumb_up(hand_landmarks, image):
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    other_fingers_y = min(index_tip.y, middle_tip.y, ring_tip.y, pinky_tip.y)
    is_up = (thumb_tip.y < thumb_mcp.y) and (thumb_tip.y < other_fingers_y)
    h, w, _ = image.shape
    text_y = 120
    cv2.putText(image, f"Thumb y: {thumb_tip.y:.2f}, Others min y: {other_fingers_y:.2f}", 
                (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    cv2.putText(image, f"Thumb up check: {is_up}", 
                (10, text_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    return is_up

def is_thumb_down(hand_landmarks, image):
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    other_fingers_y = max(index_tip.y, middle_tip.y, ring_tip.y, pinky_tip.y)
    is_down = (thumb_tip.y > thumb_mcp.y) and (thumb_tip.y > other_fingers_y)
    text_y = 160
    cv2.putText(image, f"Thumb y: {thumb_tip.y:.2f}, Others max y: {other_fingers_y:.2f}", 
                (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    cv2.putText(image, f"Thumb down check: {is_down}", 
                (10, text_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return is_down

def is_open_palm(hand_landmarks, image):
    fingertips = [
        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    ]
    pip_joints = [
        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP],
        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    ]
    fingers_extended = []
    for i in range(5):
        if i == 0:
            wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            thumb_cmc = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_CMC]
            thumb_extended = calculate_distance(fingertips[i], wrist) > calculate_distance(thumb_cmc, wrist)
        else:
            finger_extended = fingertips[i].y < pip_joints[i].y
            fingers_extended.append(finger_extended)
    is_palm = sum(fingers_extended) >= 4
    text_y = 200
    cv2.putText(image, f"Fingers extended: {fingers_extended.count(True)}/4", 
                (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.putText(image, f"Open palm: {is_palm}", 
                (10, text_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return is_palm

def is_number_one(hand_landmarks, image):
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    index_extended = index_tip.y < index_pip.y
    middle_folded = middle_tip.y > middle_pip.y
    ring_folded = ring_tip.y > ring_pip.y
    pinky_folded = pinky_tip.y > pinky_pip.y
    is_one = index_extended and middle_folded and ring_folded and pinky_folded
    text_y = 240
    cv2.putText(image, f"Index: {index_extended}, Others folded: {middle_folded and ring_folded and pinky_folded}", 
                (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    cv2.putText(image, f"Number one: {is_one}", 
                (10, text_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    return is_one

def is_number_two(hand_landmarks, image):
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    index_extended = index_tip.y < index_pip.y
    middle_extended = middle_tip.y < middle_pip.y
    ring_folded = ring_tip.y > ring_pip.y
    pinky_folded = pinky_tip.y > pinky_pip.y
    is_two = index_extended and middle_extended and ring_folded and pinky_folded
    text_y = 280
    cv2.putText(image, f"Index & Middle: {index_extended and middle_extended}, Others: {ring_folded and pinky_folded}", 
                (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 150, 0), 1)
    cv2.putText(image, f"Number two: {is_two}", 
                (10, text_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 150, 0), 1)
    return is_two

def is_rock_on(hand_landmarks, image):
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    index_extended = index_tip.y < index_pip.y
    middle_folded = middle_tip.y > middle_pip.y
    ring_folded = ring_tip.y > ring_pip.y
    pinky_extended = pinky_tip.y < pinky_pip.y
    is_rock = index_extended and middle_folded and ring_folded and pinky_extended
    text_y = 320
    cv2.putText(image, f"Index & Pinky: {index_extended and pinky_extended}, Middle & Ring: {middle_folded and ring_folded}", 
                (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 255), 1)
    cv2.putText(image, f"Rock on: {is_rock}", 
                (10, text_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 255), 1)
    return is_rock

def debug_finger_positions(hand_landmarks, image):
    fingertips = [
        ("Thumb", hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y),
        ("Index", hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y),
        ("Middle", hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y),
        ("Ring", hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y),
        ("Pinky", hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y)
    ]
    debug_y = 380
    cv2.putText(image, "Fingertip Y-values:", (10, debug_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    for i, (finger, y_val) in enumerate(fingertips):
        cv2.putText(image, f"{finger}: {y_val:.2f}", 
                    (10, debug_y + 20 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

# --- Voice Processing Functions ---
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
    except Exception as e:
        print(f"Error during NLU request: {e}", file=sys.stderr)
        time.sleep(2)
        return None

# --- Voice Control Loop ---
def voice_control_loop():
    print("\nStarting voice control loop...")
    while True:
        print("-" * 30)
        command_audio = record_audio(COMMAND_DURATION, SAMPLE_RATE, CHANNELS)
        if command_audio:
            text = get_text_from_audio(command_audio)
            if text:
                intent_result = get_intent_from_text(text)
                if intent_result and intent_result.get('intent'):
                    intent_name = intent_result['intent'].get('name', 'UnknownIntent')
                    print("\n--- Recognized Intent (Raw from Rhasspy) ---")
                    print(f"Intent: {intent_name}")
                    print(f"Confidence: {intent_result['intent'].get('confidence', 'N/A')}")
                    print("------------------------------------------")
                    custom_payload = parse_rhasspy_intent(intent_name)
                    if custom_payload:
                        publish_voice_intent(VOICE_MQTT_INTENT_TOPIC, custom_payload)
                    else:
                        print(f"Intent '{intent_name}' not mapped to custom payload. Not publishing.")
                else:
                    print("Could not recognize intent from text.")
            else:
                print("Could not transcribe audio.")
        else:
            print("Failed to record command audio. Retrying...")
            time.sleep(1)

# --- Gesture Control Loop ---
def gesture_control_loop():
    cap = cv2.VideoCapture(0)
    last_command_time = 0
    cooldown = 1.5
    action_text = ""
    text_display_end = 0
    debug_mode = True
    mqtt_status = "Connecting to MQTT..."

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Failed to read from webcam.")
            break
        image = cv2.flip(image, 1)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_image)
        current_time = time.time()
        if debug_mode:
            cv2.rectangle(image, (5, 100), (500, 480), (0, 0, 0), -1)
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                if debug_mode:
                    debug_finger_positions(hand_landmarks, image)
                if current_time - last_command_time > cooldown:
                    if is_thumb_up(hand_landmarks, image):
                        action_text = "UNLOCKING DOOR"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        mqtt_message = {"name": DOOR_NAME, "state": "unlock"}
                        publish_gesture_message(GESTURE_MQTT_TOPIC, mqtt_message)
                    elif is_thumb_down(hand_landmarks, image):
                        action_text = "LOCKING DOOR"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        mqtt_message = {"name": DOOR_NAME, "state": "lock"}
                        publish_gesture_message(GESTURE_MQTT_TOPIC, mqtt_message)
                    elif is_open_palm(hand_landmarks, image):
                        action_text = "SWITCHES ALL ON"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        mqtt_message = {"name": "CMD_SWITCH_ALL", "state": "on"}
                        publish_gesture_message(GESTURE_MQTT_TOPIC, mqtt_message)
                    elif is_number_one(hand_landmarks, image):
                        action_text = "SWITCHES ALL OFF"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        mqtt_message = {"name": "CMD_SWITCH_ALL", "state": "off"}
                        publish_gesture_message(GESTURE_MQTT_TOPIC, mqtt_message)
                    elif is_number_two(hand_landmarks, image):
                        action_text = "LIGHTS ALL ON"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        mqtt_message = {"name": "CMD_LIGHT_ALL", "state": "on"}
                        publish_gesture_message(GESTURE_MQTT_TOPIC, mqtt_message)
                    elif is_rock_on(hand_landmarks, image):
                        action_text = "LIGHTS ALL OFF"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        mqtt_message = {"name": "CMD_LIGHT_ALL", "state": "off"}
                        publish_gesture_message(GESTURE_MQTT_TOPIC, mqtt_message)
        if current_time < text_display_end:
            cv2.rectangle(image, (40, 30), (400, 70), (0, 0, 0), -1)
            cv2.putText(image, action_text, (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if current_time - last_command_time < cooldown:
            countdown = int(cooldown - (current_time - last_command_time)) + 1
            cv2.putText(image, f"Cooldown: {countdown}s", (image.shape[1] - 200, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        mqtt_status = "Connected" if gesture_client.is_connected() else "Disconnected"
        cv2.putText(image, f"MQTT: {mqtt_status}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Press 'D' to toggle debug info", (image.shape[1] - 250, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_start = image.shape[0] - 140
        cv2.putText(image, "Gesture Legend:", (10, y_start), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Thumb Up: Door UNLOCK", (10, y_start + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Thumb Down: Door LOCK", (10, y_start + 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Open Palm: SWITCHES ALL ON", (10, y_start + 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Number One: SWITCHES ALL OFF", (10, y_start + 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Number Two: LIGHTS ALL ON", (10, y_start + 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Rock On: LIGHTS ALL OFF", (10, y_start + 120), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imshow('Smart Home Control with Hand Gestures', image)
        key = cv2.waitKey(5) & 0xFF
        if key == 27:  # ESC key
            break
        elif key == ord('d') or key == ord('D'):
            debug_mode = not debug_mode
    cap.release()
    cv2.destroyAllWindows()

# --- Main Execution ---
if __name__ == "__main__":
    print("Smart Home Control System")
    print("Select control mode:")
    print("1. Gesture Control")
    print("2. Voice Control")
    print("3. Both (Gesture and Voice)")
    while True:
        choice = input("Enter choice (1, 2, or 3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")

    try:
        if choice == '2' or choice == '3':
            voice_thread = threading.Thread(target=voice_control_loop, daemon=True)
            voice_thread.start()
        if choice == '1' or choice == '3':
            gesture_control_loop()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    finally:
        gesture_client.loop_stop()
        gesture_client.disconnect()
        if voice_mqtt_client.is_connected():
            voice_mqtt_client.loop_stop()
            voice_mqtt_client.disconnect()
        print("MQTT clients disconnected. Program finished.")