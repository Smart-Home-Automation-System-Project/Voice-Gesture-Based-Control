#!/bin/bash
# Start Mycroft core services
source venv/bin/activate  # If using virtualenv
python -m mycroft.messagebus.service &
python -m mycroft.skills &
python -m mycroft.audio &
python -m mycroft.voice &
python -m mycroft.client.text &