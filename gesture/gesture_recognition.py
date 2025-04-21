import cv2
import numpy as np
import math
import mediapipe as mp

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,       # Process video stream
    max_num_hands=1,               # Detect only one hand
    min_detection_confidence=0.7,  # Minimum confidence for detection
    min_tracking_confidence=0.5)   # Minimum confidence for tracking
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- Webcam Setup ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Finger tip IDs in MediaPipe Landmarks
tip_ids = [4, 8, 12, 16, 20]

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break
    if frame is None:
        print("Warning: Received empty frame.")
        continue

    # Flip the frame horizontally for a later selfie-view display
    # And convert the BGR image to RGB.
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame and find hands
    results = hands.process(frame_rgb)

    # --- Landmark extraction and finger counting ---
    finger_count = 0
    lm_list = [] # To store landmark coordinates

    if results.multi_hand_landmarks:
        # Get the first detected hand
        hand_landmarks = results.multi_hand_landmarks[0]

        # Get landmark coordinates and store them in a list
        for id, lm in enumerate(hand_landmarks.landmark):
            h, w, c = frame.shape
            cx, cy = int(lm.x * w), int(lm.y * h)
            lm_list.append([id, cx, cy])

        # Draw landmarks and connections
        mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style())

        # --- Finger Counting Logic ---
        if len(lm_list) != 0:
            fingers = []

            # Thumb (Check x-coordinate relative to a point inside the palm)
            # Note: This logic assumes a right hand in the flipped view. Adjust if needed.
            if lm_list[tip_ids[0]][1] > lm_list[tip_ids[0] - 1][1]: # Tip x > IP joint x
                 fingers.append(1)
            else:
                 fingers.append(0)

            # Other 4 fingers (Check y-coordinate: tip vs PIP joint)
            for id in range(1, 5): # Index, Middle, Ring, Pinky
                if lm_list[tip_ids[id]][2] < lm_list[tip_ids[id] - 2][2]: # Tip y < PIP joint y
                    fingers.append(1) # Finger is open
                else:
                    fingers.append(0) # Finger is closed

            finger_count = fingers.count(1)

    # --- Display the finger count ---
    cv2.putText(frame, f"Fingers: {finger_count}", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

    # Display the frame
    cv2.imshow('Hand Tracking', frame)

    # Exit on ESC key
    k = cv2.waitKey(5) & 0xFF # Use a small delay
    if k == 27:
        break

# Release resources
hands.close()
cap.release()
cv2.destroyAllWindows()
print("Webcam released and windows closed.")
