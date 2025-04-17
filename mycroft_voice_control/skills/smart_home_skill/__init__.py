from mycroft import MycroftSkill, intent_handler
from mycroft.messagebus.message import Message
import paho.mqtt.publish as mqtt
import time

class SmartHomeSkill(MycroftSkill):
    def __init__(self):
        super().__init__(name="SmartHomeSkill")
        self.last_command_time = 0
        self.command_delay = 1  # seconds between commands

    @intent_handler('turn.on.intent')
    def handle_turn_on(self, message):
        device = message.data.get('device', 'lights')
        current_time = time.time()
        
        if current_time - self.last_command_time > self.command_delay:
            mqtt.single(
                f"smart_home/voice/{device}/command",
                "ON",
                hostname=self.config_core.get('mqtt', {}).get('host', 'localhost')
            )
            self.speak_dialog('turned.on', {'device': device})
            self.last_command_time = current_time

    @intent_handler('turn.off.intent')
    def handle_turn_off(self, message):
        device = message.data.get('device', 'lights')
        current_time = time.time()
        
        if current_time - self.last_command_time > self.command_delay:
            mqtt.single(
                f"smart_home/voice/{device}/command",
                "OFF",
                hostname=self.config_core.get('mqtt', {}).get('host', 'localhost')
            )
            self.speak_dialog('turned.off', {'device': device})
            self.last_command_time = current_time

    @intent_handler('set.temp.intent')
    def handle_set_temp(self, message):
        temp = message.data.get('temperature')
        if temp:
            mqtt.single(
                "smart_home/voice/thermostat/command",
                f"temp:{temp}",
                hostname=self.config_core.get('mqtt', {}).get('host', 'localhost')
            )
            self.speak_dialog('temperature.set', {'temp': temp})

    @intent_handler('query.status.intent')
    def handle_status_query(self, message):
        device = message.data.get('device', 'lights')
        mqtt.single(
            f"smart_home/voice/{device}/query",
            "status",
            hostname=self.config_core.get('mqtt', {}).get('host', 'localhost')
        )
        self.speak(f"Checking {device} status")

def create_skill():
    return SmartHomeSkill()