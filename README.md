# Gesture and Voice Control System for IoT Smart Home

This project implements a **gesture- and voice-based control system** for an IoT Smart Home automation platform. It enables users to control smart devices such as doors, lights, and appliances using intuitive **hand gestures** and **voice commands**.

---

## Project Overview

The system integrates real-time hand gesture recognition and voice command processing to provide a seamless user experience for controlling IoT devices. It leverages open-source libraries and MQTT for communication, ensuring scalability and extensibility.

---

## Features

### Gesture Control
- **Hand Gesture Recognition**: Utilizes MediaPipe for real-time hand landmark detection.
- **Supported Gestures**:
  - **Thumb Up**: Unlocks the front door.
  - **Thumb Down**: Locks the front door.
  - **Open Palm**: Turns all switches on.
  - **Number One (index finger up)**: Turns all switches off.
  - **Number Two (victory sign)**: Turns all lights on.
  - **Rock On (index and pinky up)**: Turns all lights off.
- **Cooldown Mechanism**: 1.5-second delay to prevent repeated gesture triggers.
- **Debug Mode**: Displays fingertip coordinates, gesture status, and MQTT connection for troubleshooting.
- **Visual Feedback**: Shows action text (e.g., "UNLOCKING DOOR") and gesture legend on the video feed.

### Voice Control
- **Voice Command Processing**: Records 5-second audio clips (16kHz, mono) and processes them using Rhasspy for speech-to-text and intent recognition.
- **Intent Recognition**: Converts spoken commands into actionable intents for smart home control.
- **Continuous Voice Listening**: Loops to detect and process voice commands until interrupted.
- **Rhasspy Integration**: Uses a local Rhasspy instance (`http://localhost:12101`) for voice processing.
- **User Feedback**: Provides console logs for voice command processing.

### System Features
- **MQTT Integration**: Enables remote monitoring and control via MQTT.
- **Error Handling**: Manages audio, speech-to-text, natural language understanding, and MQTT errors with retries and logging.
- **Configurable Device Name**: Customizable door name (e.g., "Front Door") for MQTT messages.
- **Real-Time Operation**: Ensures responsive gesture and voice command processing.
- **Extensible Design**: Modular code allows easy addition of new gestures or voice intents.
- **Open-Source Libraries**: Built with OpenCV, MediaPipe, SoundDevice, Paho MQTT, and Rhasspy.

---

## Prerequisites

### Hardware
- Webcam or camera module
- Microphone
- Raspberry Pi (version 3 or newer recommended)

### Software
- Python 3.7 or newer
- MQTT broker (default: `mqtt.local`)
- Docker and Docker Compose (for Rhasspy setup)

#### Install Docker and Docker Compose (Ubuntu)
```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp 
```
#### Also can use Docker Desktop
```bash
https://www.docker.com/products/docker-desktop/
```


**Note**: Log out and back in for group changes to take effect.

---

## Setup Instructions

# 1. Gesture Control Module

#### 1.1 Installation

##### Windows
1. **Install Python**:
   - Download and install Python from [python.org](https://python.org).
   - Ensure "Add Python to PATH" is checked during installation.
2. **Install Dependencies**:
   ```bash
   pip install opencv-python mediapipe numpy paho-mqtt
   ```
3. **Install Visual C++ Redistributable** (required for MediaPipe):
   - Download and install from [Microsoft's website](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
4. **Clone or Download the Code**:
   - Obtain the project repository from the source.

##### Ubuntu
1. **Install Python and Required Packages**:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-dev
   sudo apt install -y libopencv-dev python3-opencv
   sudo apt install -y cmake protobuf-compiler
   sudo apt install -y v4l-utils
   ```
2. **Install Dependencies**:
   ```bash
   pip install mediapipe numpy paho-mqtt
   ```
   **Note**: If MediaPipe installation fails, try:
   ```bash
   pip3 install --upgrade pip
   pip3 install mediapipe --no-binary mediapipe
   ```
3. **Clone or Download the Code**:
   - Obtain the project repository from the source.

#### 1.2 Running the Application

##### Windows
1. Open a Command Prompt.
2. Run the main script:
   ```bash
   python gesture_mqtt.py
   ```
3. To monitor MQTT messages (in a separate Command Prompt):
   ```bash
   python mqtt_listener.py
   ```

##### Ubuntu
1. Open a Terminal.
2. Make scripts executable:
   ```bash
   chmod +x gesture_mqtt.py mqtt_listener.py
   ```
3. Run the main script:
   ```bash
   python3 gesture_mqtt.py
   ```
4. To monitor MQTT messages (in a separate Terminal):
   ```bash
   python3 mqtt_listener.py
   ```

#### 1.3 Usage Instructions
1. Start the application.
2. Position yourself in front of the webcam.
3. Perform supported gestures to trigger actions.
4. Press `ESC` to exit the application.

#### 1.4 MQTT Message Format
Messages are published in JSON format:
```json
{
  "name": "device_name",
  "state": "action"
}
```
**Example**:
- Door control: `{"name": "Front Door", "state": "unlock"}`
- Switch control: `{"name": "CMD_SWITCH_ALL", "state": "on"}`

#### 1.5 Scripts
- gesture_mosquitto.py - All commands included. Use a public mqtt broker (test.mosquttio.org) for testing. 
- door_mosquitto.py - Similar to geature_mosquitto.py, only the commands relevant to door control are included. 
- mqtt_listener.py - Used for testing purposes with the above 2 files. 
In Windows - We checked whether gesture commands identifying and mqtt message sending are working correctly by running mqtt_listener.py in one command prompt and gesture_mosquitto.py or door_mosquitto.py in another command prompt. 
- door_mqtt.py - Similar to the above door_mosquitto.py but mqtt broker ip.address changed to mqtt.local
gesture_mqtt.py - The final file with the above change for identifying all gesture based commands. 

**MQTT Listener**:
- The `mqtt_listener.py` script connects to the MQTT broker, subscribes to the `central_main/control` topic, and prints received messages for debugging.

# 2. Voice Control Module

#### 2.1 Installation

##### Rhasspy Voice Assistant Setup
1. **Run Rhasspy with Docker**:
   ```bash
   docker run -d \
     --network=host \
     --name rhasspy \
     -v "$HOME/.config/rhasspy/profiles:/profiles" \
     rhasspy/rhasspy \
     --user-profiles /profiles \
     --profile en
   ```
2. Access the **Rhasspy Web UI** at: [http://localhost:12101/](http://localhost:12101/).

##### MQTT Setup
1. **Install Mosquitto (MQTT Broker)**:
   ```bash
   sudo apt update
   sudo apt install -y mosquitto mosquitto-clients
   sudo systemctl start mosquitto
   sudo systemctl enable mosquitto
   ```
2. **Verify Mosquitto is Running**:
   ```bash
   sudo systemctl status mosquitto
   ```
3. **Install Paho MQTT**:
   ```bash
   pip install paho-mqtt
   ```
4. **Check Received MQTT Messages**:
   ```bash
   mosquitto_sub -h test.mosquitto.org -p 1883 -t "rhasspy/intent/recognized" -v
   ```

##### Additional Dependencies
```bash
pip install sounddevice numpy scipy
```

#### 2.2 Configuring Rhasspy
1. Open the **Rhasspy Web UI**.
2. Navigate to the **Sentences Tab**.
3. Copy and paste the contents of `sentences.ini` into the editor to define recognized intents.

#### 2.3 Scripts
- **jarvis.py**: Under development; will include wake word functionality.
- **voiceControl.py**: Processes voice commands without a wake word.

#### 2.4 Verifying Commands
To confirm Rhasspy receives voice commands via MQTT:
```bash
mosquitto_sub -h test.mosquitto.org -p 1883 -t "rhasspy/intent/recognized" -v
```

#### 2.5 Usage Instructions
1. Ensure Docker and Mosquitto are running.
2. Configure `sentences.ini` in the Rhasspy Web UI.
3. Run `voiceControl.py` to process voice commands.
4. To run the gesture_control_system in `ubuntu`
   first run the following
   ```bash
   pip install -r ubuntu_requirements.txt
   ```

---

## Development

### Testing
- Unit Test scripts are available in the `test` folder.
- Review and adapt these scripts to verify functionality or customize for your setup.

---

## to run the gedture_control_system in ubuntu,first run the following:
pip install -r ubuntu_requirements.txt