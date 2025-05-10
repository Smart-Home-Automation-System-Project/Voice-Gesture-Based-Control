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
#mqtt_broker = "test.mosquitto.org"  # Public MQTT broker for testing
mqtt_broker = "mqtt.localhost"  # Local MQTT broker
mqtt_port = 1883
mqtt_topic = "central_main/control"  # Updated topic for central system

# Device configuration
door_name = "Font Door"  # Name of the door to control

# MQTT Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

def on_publish(client, userdata, mid, properties=None):
    print(f"Message {mid} published")

# Set up MQTT client with the correct protocol version
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_publish = on_publish
client.connect(mqtt_broker, mqtt_port)
client.loop_start()  # Start the background thread

# MQTT Publish function
def publish_message(topic, message_dict):
    message_json = json.dumps(message_dict)
    result = client.publish(topic, message_json)
    status = result[0]
    if status == 0:
        print(f"Message sent to topic {topic}: {message_json}")
    else:
        print(f"Failed to send message to topic {topic}")

# Gesture Detection Functions with debug information
def calculate_distance(point1, point2):
    return math.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)

def is_thumb_up(hand_landmarks, image):
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
    
    # More robust check for thumb up - check if it's significantly above other fingers
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    
    # Check if thumb is higher than other folded fingers and extended upward
    other_fingers_y = min(index_tip.y, middle_tip.y, ring_tip.y, pinky_tip.y)
    is_up = (thumb_tip.y < thumb_mcp.y) and (thumb_tip.y < other_fingers_y)
    
    # Add debug text
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
    
    # Check other fingers position
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    
    # Check if thumb is lower than other folded fingers and pointing downward
    other_fingers_y = max(index_tip.y, middle_tip.y, ring_tip.y, pinky_tip.y)
    is_down = (thumb_tip.y > thumb_mcp.y) and (thumb_tip.y > other_fingers_y)
    
    # Add debug text
    text_y = 160
    cv2.putText(image, f"Thumb y: {thumb_tip.y:.2f}, Others max y: {other_fingers_y:.2f}", 
                (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    cv2.putText(image, f"Thumb down check: {is_down}", 
                (10, text_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    return is_down

def debug_finger_positions(hand_landmarks, image):
    # Display y-coordinates of fingertips for debugging
    fingertips = [
        ("Thumb", hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y),
        ("Index", hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y),
        ("Middle", hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y),
        ("Ring", hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y),
        ("Pinky", hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y)
    ]
    
    debug_y = 320
    cv2.putText(image, "Fingertip Y-values:", (10, debug_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    for i, (finger, y_val) in enumerate(fingertips):
        cv2.putText(image, f"{finger}: {y_val:.2f}", 
                    (10, debug_y + 20 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

def main(mqtt_client=None):
    # Use the provided MQTT client or create a new one
    global client
    client = mqtt_client or mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.connect(mqtt_broker, mqtt_port)
    client.loop_start()  # Start the background thread

    # Open webcam
    cap = cv2.VideoCapture(0)
    
    # Command cooldown to prevent multiple detections
    last_command_time = 0
    cooldown = 1.5  # seconds
    
    # For showing the action text
    action_text = ""
    text_display_end = 0
    
    # Debug mode
    debug_mode = True
    
    # MQTT connection status display
    mqtt_status = "Connecting to MQTT..."
    
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Failed to read from webcam.")
            break
        
        # Flip the image horizontally for a selfie-view display
        image = cv2.flip(image, 1)
        
        # Convert the BGR image to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_image)
        
        # Current time for cooldown
        current_time = time.time()
        
        # Clear debug area
        if debug_mode:
            cv2.rectangle(image, (5, 100), (400, 400), (0, 0, 0), -1)
        
        # Draw hand landmarks
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Display debug info for finger positions
                if debug_mode:
                    debug_finger_positions(hand_landmarks, image)
                
                # Gesture recognition
                if current_time - last_command_time > cooldown:
                    # Check gestures with debug info
                    if is_thumb_up(hand_landmarks, image):
                        action_text = "UNLOCKING DOOR"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        
                        # Send MQTT message for door unlock
                        mqtt_message = {
                            "name": door_name,
                            "state": "unlock"  # "unlock" instead of 0
                        }
                        publish_message(mqtt_topic, mqtt_message)
                        
                    elif is_thumb_down(hand_landmarks, image):
                        action_text = "LOCKING DOOR"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                        
                        # Send MQTT message for door lock
                        mqtt_message = {
                            "name": door_name,
                            "state": "lock"  # "lock" instead of 1
                        }
                        publish_message(mqtt_topic, mqtt_message)
        
        # Display action text if within display time
        if current_time < text_display_end:
            # Draw a background for better visibility
            cv2.rectangle(image, (40, 30), (400, 70), (0, 0, 0), -1)
            cv2.putText(image, action_text, (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Show command cooldown timer
        if current_time - last_command_time < cooldown:
            countdown = int(cooldown - (current_time - last_command_time)) + 1
            cv2.putText(image, f"Cooldown: {countdown}s", (image.shape[1] - 200, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display MQTT status
        if client.is_connected():
            mqtt_status = "Connected"
        else:
            mqtt_status = "Disconnected"
        cv2.putText(image, f"MQTT: {mqtt_status}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display debug toggle instruction
        cv2.putText(image, "Press 'D' to toggle debug info", (image.shape[1] - 250, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display legend for gestures
        cv2.putText(image, "Thumb Up: Door UNLOCK", (10, image.shape[0] - 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Thumb Down: Door LOCK", (10, image.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display the image
        cv2.imshow('Door Control with Hand Gestures', image)
        
        # Process keyboard input
        key = cv2.waitKey(5) & 0xFF
        if key == 27:  # ESC key to exit
            break
        elif key == ord('d') or key == ord('D'):  # D key to toggle debug
            debug_mode = not debug_mode
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
