```markdown
# Rhasspy Voice Assistant Setup

This project sets up Rhasspy, a voice assistant that works with MQTT to recognize spoken commands. Below are the correct installation steps, dependencies, and configurations needed for the system to function properly.

---

## Prerequisites

Ensure your system is up to date and install necessary dependencies:

```sh
sudo apt update
sudo apt install docker.io docker-compose -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

You might need to **log out and log back in** for the group change to take effect:

```sh
newgrp docker
```

---

## Installing & Running Rhasspy

Use the **correct** method to run Rhasspy:

```sh
docker run -d \
  --network=host \
  --name rhasspy \
  -v "$HOME/.config/rhasspy/profiles:/profiles" \
  rhasspy/rhasspy \
  --user-profiles /profiles \
  --profile en
```

Once running, you can access the **Rhasspy Web UI** at:

👉 [http://localhost:12101/](http://localhost:12101/)

---

## MQTT Setup

Install **Mosquitto** (MQTT broker) and clients:

```sh
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

Ensure **Mosquitto** is running:

```sh
sudo systemctl start mosquitto
```

Install **paho-mqtt** Python package:

```sh
pip install paho-mqtt
```

To **check received MQTT messages**, use:

```sh
mosquitto_sub -h test.mosquitto.org -p 1883 -t "rhasspy/intent/recognized" -v
```

---

## Additional Dependencies

Ensure you have the required Python packages installed:

```sh
pip install sounddevice numpy scipy
```

---

## Configuring Sentences for Rhasspy

The `sentences.ini` file contains **intents recognized** by Rhasspy.

- Open **Rhasspy Web UI**.
- Navigate to the **Sentences Tab**.
- Copy and paste your `sentences.ini` file into the editor.

---

## Voice Control

- The main script **`jarvis.py`** is still being implemented to work with a **wake word**.
- However, the **`voiceControl.py`** script functions **without a wake word** and can process commands.

---

## Verifying Commands

To check if Rhasspy has **correctly received voice commands via MQTT**, use:

```sh
mosquitto_sub -h test.mosquitto.org -p 1883 -t "rhasspy/intent/recognized" -v
```

---

## Notes

- Ensure the **correct Docker setup** is used (avoid incorrect methods).
- Make sure **Mosquitto** is running before testing MQTT subscriptions.
- Configure voice command recognition properly in `sentences.ini`.

---

## Credits

This setup is based on Rhasspy, an open-source voice assistant framework.

# Gesture Commands 

gesture_mosquitto.py - All commands included. Use a public mqtt broker (test.mosquttio.org) for testing. 
door_mosquitto.py - Similar to geature_mosquitto.py, only the commands relevant to door control are included. 
mqtt_listener.py - Used for testing purposes with the above 2 files. 
In Windows - We checked whether gesture commands identifying and mqtt message sending are working correctly by running mqtt_listener.py in one command prompt and gesture_mosquitto.py or door_mosquitto.py in another command prompt. 

door_mqtt.py - Similar to the above door_mosquitto.py but mqtt broker ip.address changed to mqtt.local
gesture_mqtt.py - The final file with the above change for identifying all gesture based commands. 

# MQTT Listener
The project includes an MQTT listener script (mqtt_listener.py) that can be used for testing and debugging purposes. This script:

Connects to the MQTT broker
Subscribes to the central_main/control topic
Prints all messages received on this topic

This is useful for:

Verifying that gesture commands are being correctly published
Debugging connection issues
Monitoring smart home control messages

The MQTT listener can be run in parallel with the main gesture control application to see the MQTT messages in real-time as gestures are recognized.

## gesture_mqtt.py
# Features

Real-time hand tracking and gesture recognition using MediaPipe
MQTT integration for smart home control
Supported gestures:

👍 Thumb Up: Unlock door
👎 Thumb Down: Lock door
✋ Open Palm: Turn all switches on
☝️ Number One: Turn all switches off
✌️ Number Two: Turn all lights on
🤘 Rock On: Turn all lights off


Visual feedback for actions and cooldown period

# Prerequisites

Python 3.7 or newer
Webcam
MQTT broker (The code uses mqtt.local as the broker address)

# Installation
Windows

Install Python:

Download and install Python from python.org
Make sure to check "Add Python to PATH" during installation


Install dependencies:
cmdpip install opencv-python mediapipe numpy paho-mqtt

Install Visual C++ Redistributable (required for MediaPipe):

Download and install the latest Visual C++ Redistributable from Microsoft's website


Clone or download the code
------------------
Ubuntu

Install Python and required packages:
bashsudo apt update
sudo apt install -y python3 python3-pip python3-dev
sudo apt install -y libopencv-dev python3-opencv
sudo apt install -y cmake protobuf-compiler

Install dependencies:
bashpip3 install mediapipe numpy paho-mqtt
Note: If you encounter issues with MediaPipe installation, try:
bashpip3 install --upgrade pip
pip3 install mediapipe --no-binary mediapipe

Install additional libraries for webcam support:
bashsudo apt install -y v4l-utils

Clone or download the code

# Running the Application
Windows

Open Command Prompt
Run the script:
cmdpython gesture_control.py
To monitor MQTT messages (in a separate Command Prompt):
cmdpython mqtt_listener.py (for this need to run gesture_mosquitto.py)
-------------------
Ubuntu

Open Terminal

Make the scripts executable:
bashchmod +x gesture_control.py mqtt_listener.py

Run the main script:
bashpython3 gesture_control.py

To monitor MQTT messages (in a separate Terminal):
bashpython3 mqtt_listener.py

# Usage Instructions

Start the application
Position yourself in front of your webcam
Perform the supported gestures to trigger actions
Press 'ESC' to exit the application

# MQTT Message Format
Messages are published in JSON format:
json{
  "name": "device_name",
  "state": "action"
}
Examples:

Door control: {"name": "Front Door", "state": "unlock"}
Switch control: {"name": "CMD_SWITCH_ALL", "state": "on"}

