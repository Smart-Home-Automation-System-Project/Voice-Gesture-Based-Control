import cv2
import mediapipe as mp
import numpy as np
import time
import math
import json
import paho.mqtt.client as mqtt

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# MQTT Configuration
mqtt_broker = "test.mosquitto.org"
mqtt_port = 1883
mqtt_topic_door = "home/automation/Door1_control"
mqtt_topic_light = "home/automation/Light1_control"

# MQTT Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

def on_publish(client, userdata, mid, properties=None):
    print(f"Message {mid} published")

# Set up MQTT client
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_publish = on_publish
client.connect(mqtt_broker, mqtt_port)
client.loop_start()

# MQTT Publish function
def publish_message(topic, message_dict):
    message_json = json.dumps(message_dict)
    result = client.publish(topic, message_json)
    status = result[0]
    if status == 0:
        print(f"Message sent to topic {topic}: {message_json}")
    else:
        print(f"Failed to send message to topic {topic}")

# Gesture detection helpers
def is_thumb_up(hand_landmarks, image):
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]

    other_fingers_y = min(index_tip.y, middle_tip.y, ring_tip.y, pinky_tip.y)
    is_up = (thumb_tip.y < thumb_mcp.y) and (thumb_tip.y < other_fingers_y)

    cv2.putText(image, f"Thumb Up: {is_up}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
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

    cv2.putText(image, f"Thumb Down: {is_down}", (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return is_down

def is_index_finger_up(hand_landmarks, image):
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    other_fingers_folded = True

    for finger in [
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP,
        mp_hands.HandLandmark.THUMB_TIP
    ]:
        tip = hand_landmarks.landmark[finger]
        pip = hand_landmarks.landmark[finger - 2]
        if tip.y < pip.y:
            other_fingers_folded = False

    is_up = index_tip.y < index_pip.y and other_fingers_folded
    cv2.putText(image, f"Index Up: {is_up}", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    return is_up

def is_fist(hand_landmarks, image):
    folded = True
    for finger_tip in [
        mp_hands.HandLandmark.THUMB_TIP,
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP,
    ]:
        tip = hand_landmarks.landmark[finger_tip]
        mcp = hand_landmarks.landmark[finger_tip - 3]
        if tip.y < mcp.y:
            folded = False
            break
    cv2.putText(image, f"Fist: {folded}", (10, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 100), 1)
    return folded

# Main program
def main():
    global client
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
            cv2.rectangle(image, (5, 100), (400, 300), (0, 0, 0), -1)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                if current_time - last_command_time > cooldown:
                    if is_thumb_up(hand_landmarks, image):
                        action_text = "OPENING DOOR"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        publish_message(mqtt_topic_door, {"name": "Door1", "type": "Door", "value": 0})

                    elif is_thumb_down(hand_landmarks, image):
                        action_text = "CLOSING DOOR"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        publish_message(mqtt_topic_door, {"name": "Door1", "type": "Door", "value": 1})

                    elif is_index_finger_up(hand_landmarks, image):
                        action_text = "LIGHT ON"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        publish_message(mqtt_topic_light, {"name": "Light1", "type": "Light", "value": 1})

                    elif is_fist(hand_landmarks, image):
                        action_text = "LIGHT OFF"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        publish_message(mqtt_topic_light, {"name": "Light1", "type": "Light", "value": 0})

        if current_time < text_display_end:
            cv2.rectangle(image, (40, 30), (400, 70), (0, 0, 0), -1)
            cv2.putText(image, action_text, (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        if current_time - last_command_time < cooldown:
            countdown = int(cooldown - (current_time - last_command_time)) + 1
            cv2.putText(image, f"Cooldown: {countdown}s", (image.shape[1] - 200, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        mqtt_status = "Connected" if client.is_connected() else "Disconnected"
        cv2.putText(image, f"MQTT: {mqtt_status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Press 'D' to toggle debug info", (image.shape[1] - 250, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Gesture legends
        cv2.putText(image, "Thumb Up: Door OPEN", (10, image.shape[0] - 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Thumb Down: Door CLOSE", (10, image.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Index Finger: Light ON", (10, image.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Fist: Light OFF", (10, image.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow('Gesture Control', image)

        key = cv2.waitKey(5) & 0xFF
        if key == 27:  # ESC
            break
        elif key == ord('d') or key == ord('D'):
            debug_mode = not debug_mode

    cap.release()
    cv2.destroyAllWindows()
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
