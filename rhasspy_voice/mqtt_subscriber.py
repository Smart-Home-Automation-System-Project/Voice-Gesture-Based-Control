import paho.mqtt.client as mqtt

# Configuration
BROKER = "test.mosquitto.org"
PORT = 1883
TOPICS = ["rhasspy/intent/recognized", "central_main/control"]

# Callbacks
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT broker")
        for topic in TOPICS:
            client.subscribe(topic)
            print(f"Subscribed to {topic}")
    else:
        print(f"Connection failed, reason code {reason_code}")

def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode()}")

# Setup MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

# Connect and start loop
client.connect(BROKER, PORT, 60)
client.loop_forever()