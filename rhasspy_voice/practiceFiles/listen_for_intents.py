# filepath: /home/k-indunil/Rhasspy0.1/listen_for_intents.py
import paho.mqtt.client as mqtt
import json
import sys

RHASSPY_MQTT_HOST = "localhost"
RHASSPY_MQTT_PORT = 12183 # Default Rhasspy MQTT port
INTENT_TOPIC = "hermes/intent/#" # Subscribe to all intents

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    print(f"Connected to MQTT broker with result code {rc}")
    # Subscribe to the intent topic upon connection
    client.subscribe(INTENT_TOPIC)
    print(f"Subscribed to topic: {INTENT_TOPIC}")

def on_message(client, userdata, msg):
    """Callback when a message is received."""
    print("-" * 20)
    print(f"Received message on topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        intent_name = payload.get('intent', {}).get('intentName', 'UnknownIntent')
        confidence = payload.get('intent', {}).get('confidenceScore', 'N/A')
        site_id = payload.get('siteId', 'default')
        session_id = payload.get('sessionId', '')

        print(f"Intent Detected: {intent_name}")
        print(f"Confidence: {confidence}")
        print(f"Site ID: {site_id}")
        # print(f"Session ID: {session_id}") # Uncomment if needed
        # print("Full Payload:") # Uncomment to see everything
        # print(json.dumps(payload, indent=2)) # Uncomment to see everything

    except json.JSONDecodeError:
        print("Error decoding JSON payload.")
        print(f"Raw payload: {msg.payload}")
    except Exception as e:
        print(f"An error occurred processing the message: {e}", file=sys.stderr)
    print("-" * 20)


# Create and configure MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"Attempting to connect to MQTT broker at {RHASSPY_MQTT_HOST}:{RHASSPY_MQTT_PORT}...")
    client.connect(RHASSPY_MQTT_HOST, RHASSPY_MQTT_PORT, 60)

    # Start the MQTT loop (this runs forever until interrupted)
    print("MQTT client started. Waiting for intents...")
    client.loop_forever()

except ConnectionRefusedError:
    print(f"Error: Connection to MQTT broker refused. Is Rhasspy running and MQTT enabled?", file=sys.stderr)
except Exception as e:
    print(f"An unexpected error occurred: {e}", file=sys.stderr)
finally:
    print("\nMQTT client stopped.")
