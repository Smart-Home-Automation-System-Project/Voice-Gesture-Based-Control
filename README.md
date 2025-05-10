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
