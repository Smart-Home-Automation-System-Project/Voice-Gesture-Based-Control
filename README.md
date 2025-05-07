# to run the system in ubuntu, just run the following:
pip install -r ubuntu_requirements.txt

# Voice-Gesture-Based-Control (Gesture Control Module)

This part of the project implements a smart home automation control system using hand gestures (via MediaPipe and OpenCV).

## Features

*   **Gesture Control:**
    *   Uses OpenCV for webcam input and MediaPipe for hand landmark detection.
    *   Recognizes specific hand gestures (e.g., thumb up/down) to control devices (e.g., a door).
    *   Publishes gesture commands via MQTT.

## Setup & Usage

### Prerequisites

*   Python 3.x
*   An MQTT broker (e.g., Mosquitto) accessible by the control script.
*   Webcam.

### Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone https://github.com/Smart-Home-Automation-System-Project/Voice-Gesture-Based-Control.git
    cd Voice-Gesture-Based-Control
    ```
2.  **Navigate to the gesture control directory:**
    ```bash
    cd gestureControl
    ```
3.  **Create and activate a virtual environment (recommended, if not done at project root):**
    ```bash
    python3 -m venv .venv_gesture
    source .venv_gesture/bin/activate 
    # Or activate the project's main .venv if preferred and it contains the gesture dependencies
    ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(This typically includes `opencv-python`, `mediapipe`, `paho-mqtt`)*

### Running the Gesture Control System

1.  **Start an MQTT Broker:** Ensure your MQTT broker is running.
2.  **Run Gesture Control Script:**
    Navigate to the `gestureControl` directory (if not already there) and run:
    ```bash
    python3 door_mqtt.py
    ```
    *(This will activate the webcam for gesture detection and start publishing commands.)*

3.  **(Optional) MQTT Listener for debugging/verification:**
    You can use `mqtt_listener.py` (also in the `gestureControl` directory) or a tool like `mosquitto_sub` to monitor MQTT messages published by the gesture script.
    ```bash
    # In gestureControl directory
    # python3 mqtt_listener.py
    # OR
    # mosquitto_sub -h <your_broker_address> -t "home/automation/Door1_control" -v 
    # (or the specific topic your door_mqtt.py publishes to)
    ```

## Key Technologies

*   Python
*   OpenCV (Computer Vision)
*   MediaPipe (Hand Tracking)
*   Paho-MQTT (MQTT Communication)
```

**To update your `README.md` file:**

1.  Open `/home/k-indunil/Rhasspy0.1/README.md` in your editor.
2.  Replace its current content with the content provided above.
3.  Save the file.
4.  Commit and push the change to your GitHub repository:
    ````bash
    cd /home/k-indunil/Rhasspy0.1
    git add README.md
    git commit -m "Focus README on gesture control details"
    git push origin k4_voice_rhasspy
    ````# Voice-Gesture-Based-Control (Gesture Control Module)

This part of the project implements a smart home automation control system using hand gestures (via MediaPipe and OpenCV).

## Features

*   **Gesture Control:**
    *   Uses OpenCV for webcam input and MediaPipe for hand landmark detection.
    *   Recognizes specific hand gestures (e.g., thumb up/down) to control devices (e.g., a door).
    *   Publishes gesture commands via MQTT.

## Setup & Usage

### Prerequisites

*   Python 3.x
*   An MQTT broker (e.g., Mosquitto) accessible by the control script.
*   Webcam.

### Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone https://github.com/Smart-Home-Automation-System-Project/Voice-Gesture-Based-Control.git
    cd Voice-Gesture-Based-Control
    ```
2.  **Navigate to the gesture control directory:**
    ```bash
    cd gestureControl
    ```
3.  **Create and activate a virtual environment (recommended, if not done at project root):**
    ```bash
    python3 -m venv .venv_gesture
    source .venv_gesture/bin/activate 
    # Or activate the project's main .venv if preferred and it contains the gesture dependencies
    ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(This typically includes `opencv-python`, `mediapipe`, `paho-mqtt`)*

### Running the Gesture Control System

1.  **Start an MQTT Broker:** Ensure your MQTT broker is running.
2.  **Run Gesture Control Script:**
    Navigate to the `gestureControl` directory (if not already there) and run:
    ```bash
    python3 door_mqtt.py
    ```
    *(This will activate the webcam for gesture detection and start publishing commands.)*

3.  **(Optional) MQTT Listener for debugging/verification:**
    You can use `mqtt_listener.py` (also in the `gestureControl` directory) or a tool like `mosquitto_sub` to monitor MQTT messages published by the gesture script.
    ```bash
    # In gestureControl directory
    # python3 mqtt_listener.py
    # OR
    # mosquitto_sub -h <your_broker_address> -t "home/automation/Door1_control" -v 
    # (or the specific topic your door_mqtt.py publishes to)
    ```

## Key Technologies

*   Python
*   OpenCV (Computer Vision)
*   MediaPipe (Hand Tracking)
*   Paho-MQTT (MQTT Communication)
```

