import paho.mqtt.client as mqtt
import json
import socket
import time

# MQTT broker settings
broker = "broker.hivemq.com"
port = 1883
topic = "sasmitha/door/status"

# JSON message
message = {"name": "Font Door", "state": "lock"}

# Create MQTT client with MQTT v5
client = mqtt.Client(protocol=mqtt.MQTTv5)
connected = False

try:
    # Connect to broker with a timeout
    client.connect(broker, port, keepalive=60)
    connected = True
    print(f"Connected to broker at {broker}")

    # Wait briefly to ensure subscriber is ready
    time.sleep(2)

    # Publish the JSON message with QoS=1
    client.publish(topic, json.dumps(message), qos=1)
    print(f"Published message: {message} to topic: {topic}")

except socket.gaierror as e:
    print(f"Failed to resolve broker address: {e}")
except ConnectionRefusedError as e:
    print(f"Connection refused by broker: {e}")
except Exception as e:
    print(f"Failed to connect or publish: {e}")

finally:
    if connected:
        try:
            client.disconnect()
            print("Disconnected from broker")
        except Exception as e:
            print(f"Failed to disconnect: {e}")