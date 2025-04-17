import cv2
import mediapipe as mp
import numpy as np
import time
import math

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# Gesture Detection Functions with debug information
def calculate_distance(point1, point2):
    return math.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)

def is_thumb_up(hand_landmarks, image):
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    
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

def is_open_palm(hand_landmarks, image):
    # Get fingertips
    tips = [
        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    ]
    
    # Get finger pip joints (middle knuckles)
    pips = [
        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP],
        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    ]
    
    # Get finger mcp joints (base knuckles)
    mcps = [
        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP],
        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP],
        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP],
        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP],
        hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]
    ]
    
    # Calculate extended fingers
    extended_fingers = 0
    for i in range(5):
        # For thumb we check if it's extended sideways
        if i == 0:  # Thumb
            if tips[i].x < mcps[i].x:  # If hand is right hand
                extended = tips[i].x < mcps[i].x - 0.05
            else:  # If hand is left hand
                extended = tips[i].x > mcps[i].x + 0.05
        else:  # Other fingers
            # A finger is extended if tip is above pip
            extended = tips[i].y < pips[i].y
        
        if extended:
            extended_fingers += 1
    
    # Debug info
    cv2.putText(image, f"Extended fingers: {extended_fingers}", 
                (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    return extended_fingers >= 4

def is_closed_fist(hand_landmarks, image):
    finger_tips = [
        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    ]
    
    finger_pips = [
        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    ]
    
    # Count folded fingers (tip below pip)
    folded_fingers = 0
    for tip, pip in zip(finger_tips, finger_pips):
        if tip.y > pip.y:
            folded_fingers += 1
    
    # Check thumb position - closer to palm for a fist
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    palm_center_x = (hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x + 
                    hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].x) / 2
    palm_center_y = (hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y + 
                    hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].y) / 2
    
    thumb_to_palm_dist = math.sqrt((thumb_tip.x - palm_center_x)**2 + (thumb_tip.y - palm_center_y)**2)
    
    # Debug info
    cv2.putText(image, f"Folded fingers: {folded_fingers}, Thumb dist: {thumb_to_palm_dist:.2f}", 
                (10, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    return folded_fingers >= 3 and thumb_to_palm_dist < 0.15

# New function for number "1" gesture (index finger up, others down)
def is_number_one(hand_landmarks, image):
    # Check if index finger is extended and others are bent
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    
    # Index finger extended
    index_extended = index_tip.y < index_pip.y
    
    # Other fingers folded
    middle_folded = middle_tip.y > middle_pip.y
    ring_folded = ring_tip.y > ring_pip.y
    pinky_folded = pinky_tip.y > pinky_pip.y
    
    # Debug info
    cv2.putText(image, f"Number 1: index={index_extended}, middle={middle_folded}, ring={ring_folded}, pinky={pinky_folded}", 
                (10, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    
    return index_extended and middle_folded and ring_folded and pinky_folded

# New function for number "2" gesture (index and middle fingers up, others down)
def is_number_two(hand_landmarks, image):
    # Check if index and middle fingers are extended and others are bent
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    
    # Index and middle fingers extended
    index_extended = index_tip.y < index_pip.y
    middle_extended = middle_tip.y < middle_pip.y
    
    # Other fingers folded
    ring_folded = ring_tip.y > ring_pip.y
    pinky_folded = pinky_tip.y > pinky_pip.y
    
    # Debug info
    cv2.putText(image, f"Number 2: idx={index_extended}, mid={middle_extended}, ring={ring_folded}, pinky={pinky_folded}", 
                (10, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    
    return index_extended and middle_extended and ring_folded and pinky_folded

# New function for number "3" gesture (index, middle, and ring fingers up, others down)
def is_number_three(hand_landmarks, image):
    # Check if index, middle, and ring fingers are extended and others are bent
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    
    # Three fingers extended
    index_extended = index_tip.y < index_pip.y
    middle_extended = middle_tip.y < middle_pip.y
    ring_extended = ring_tip.y < ring_pip.y
    
    # Pinky folded
    pinky_folded = pinky_tip.y > pinky_pip.y
    
    # Debug info
    cv2.putText(image, f"Number 3: idx={index_extended}, mid={middle_extended}, ring={ring_extended}, pinky={pinky_folded}", 
                (10, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
    
    return index_extended and middle_extended and ring_extended and pinky_folded

# Updated function for "rock on" gesture (index and pinky fingers up, others down)
def is_rock_on_gesture(hand_landmarks, image):
    # Check if index and pinky fingers are extended while others are bent
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]
    
    # Index and pinky fingers extended
    index_extended = index_tip.y < index_pip.y
    pinky_extended = pinky_tip.y < pinky_pip.y
    
    # Middle and ring fingers folded
    middle_folded = middle_tip.y > middle_pip.y
    ring_folded = ring_tip.y > ring_pip.y
    
    # Debug info
    cv2.putText(image, f"Rock on: idx={index_extended}, pinky={pinky_extended}, mid/ring folded={middle_folded and ring_folded}", 
                (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (165, 0, 255), 1)
    
    return index_extended and pinky_extended and middle_folded and ring_folded

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

def main():
    # Open webcam
    cap = cv2.VideoCapture(0)
    
    # Command cooldown to prevent multiple detections
    last_command_time = 0
    cooldown = 1.5  # seconds (reduced from 2s)
    
    # For showing the action text
    action_text = ""
    text_display_end = 0
    
    # Debug mode
    debug_mode = True
    
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
                        action_text = "Lights ON"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                    
                    elif is_thumb_down(hand_landmarks, image):
                        action_text = "Lights OFF"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                    
                    elif is_open_palm(hand_landmarks, image):
                        action_text = "Door OPEN"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                    
                    elif is_closed_fist(hand_landmarks, image):
                        action_text = "Door CLOSE"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                    
                    # Check number gestures
                    elif is_number_one(hand_landmarks, image):
                        action_text = "Temperature UP"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                    
                    elif is_number_two(hand_landmarks, image):
                        action_text = "Temperature DOWN"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                    
                    elif is_number_three(hand_landmarks, image):
                        action_text = "Microwave ON"
                        text_display_end = current_time + 2
                        last_command_time = current_time
                    
                    elif is_rock_on_gesture(hand_landmarks, image):
                        action_text = "Microwave OFF"
                        text_display_end = current_time + 2
                        last_command_time = current_time
        
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
        
        # Display debug toggle instruction
        cv2.putText(image, "Press 'D' to toggle debug info", (image.shape[1] - 250, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display legend for gestures
        cv2.putText(image, "Thumb Up: Lights ON", (10, image.shape[0] - 160), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Thumb Down: Lights OFF", (10, image.shape[0] - 140), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Open Palm: Door OPEN", (10, image.shape[0] - 120), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Closed Fist: Door CLOSE", (10, image.shape[0] - 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Number 1: Temperature UP", (10, image.shape[0] - 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Number 2: Temperature DOWN", (10, image.shape[0] - 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Number 3: Microwave ON", (10, image.shape[0] - 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "Rock On: Microwave OFF", (10, image.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display the image
        cv2.imshow('Hand Gesture Control', image)
        
        # Process keyboard input
        key = cv2.waitKey(5) & 0xFF
        if key == 27:  # ESC key to exit
            break
        elif key == ord('d') or key == ord('D'):  # D key to toggle debug
            debug_mode = not debug_mode
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()