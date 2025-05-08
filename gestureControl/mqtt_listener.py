import paho.mqtt.client as mqtt

# The callback for when a message is received
def on_message(client, userdata, msg, properties=None):
    print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")

# The callback for when the client connects
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    # Subscribe to the door control topic
    client.subscribe("central_main/control")
    print("Subscribed to central_main/control")
    print("Waiting for messages...")

# Create client instance with correct API version
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)

# Assign callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect to the broker
print("Connecting to MQTT broker test.mosquitto.org...")
client.connect("test.mosquitto.org", 1883, 60)

# Start the loop to process network traffic
print("Starting MQTT listener...")
client.loop_forever()
