from speech_recognition import Recognizer, Microphone
import time
import os
import RPi.GPIO as GPIO

# GPIO Setup
# Light pins
L1_PIN = 17
L2_PIN = 27
L3_PIN = 22
L4_PIN = 23

# Door servo pins
D1_PIN = 18
D2_PIN = 24
D3_PIN = 25

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Initialize light outputs
GPIO.setup(L1_PIN, GPIO.OUT)
GPIO.setup(L2_PIN, GPIO.OUT)
GPIO.setup(L3_PIN, GPIO.OUT)
GPIO.setup(L4_PIN, GPIO.OUT)

# Turn all lights off initially
GPIO.output(L1_PIN, GPIO.LOW)
GPIO.output(L2_PIN, GPIO.LOW)
GPIO.output(L3_PIN, GPIO.LOW)
GPIO.output(L4_PIN, GPIO.LOW)

# Initialize door servos
GPIO.setup(D1_PIN, GPIO.OUT)
GPIO.setup(D2_PIN, GPIO.OUT)
GPIO.setup(D3_PIN, GPIO.OUT)

# Create PWM instances for doors
d1_servo = GPIO.PWM(D1_PIN, 50)  # 50Hz PWM frequency
d2_servo = GPIO.PWM(D2_PIN, 50)
d3_servo = GPIO.PWM(D3_PIN, 50)

# Start all servos
d1_servo.start(0)
d2_servo.start(0)
d3_servo.start(0)

def set_door(door_num, position):
    """Control servo to open/close specific door"""
    servo = None
    if door_num == 1:
        servo = d1_servo
    elif door_num == 2:
        servo = d2_servo
    elif door_num == 3:
        servo = d3_servo
    
    if servo:
        if position == "open":
            servo.ChangeDutyCycle(7.5)  # 90 degrees (open position)
            print(f"🚪 Door {door_num} opened")
        elif position == "close":
            servo.ChangeDutyCycle(2.5)  # 0 degrees (closed position)
            print(f"🚪 Door {door_num} closed")
        time.sleep(1)  # Give servo time to move
        servo.ChangeDutyCycle(0)  # Stop sending signal

def set_all_doors(position):
    """Control all doors at once"""
    for door_num in range(1, 4):
        set_door(door_num, position)

def set_light(light_num, state):
    """Control specific light"""
    pin = None
    if light_num == 1:
        pin = L1_PIN
    elif light_num == 2:
        pin = L2_PIN
    elif light_num == 3:
        pin = L3_PIN
    elif light_num == 4:
        pin = L4_PIN
    
    if pin:
        GPIO.output(pin, GPIO.HIGH if state == "on" else GPIO.LOW)
        print(f"💡 Light {light_num} turned {'ON' if state == 'on' else 'OFF'}")

def set_all_lights(state):
    """Control all lights at once"""
    for light_num in range(1, 5):
        set_light(light_num, state)

def get_microphone_index():
    """Try to find the correct microphone index"""
    try:
        print("Available microphones:")
        for index, name in enumerate(Microphone.list_microphone_names()):
            print(f"{index}: {name}")
            
        for index, name in enumerate(Microphone.list_microphone_names()):
            if "analog" in name.lower() or "input" in name.lower():
                print(f"\n🔊 Selecting microphone: {name} (index {index})")
                return index
                
        print("\n Couldn't find analog input, using default (index 0)")
        return 0
    except:
        return 0

def listen_for_command(prompt=None, timeout=3):
    recognizer = Recognizer()
    mic_index = get_microphone_index()
    
    try:
        with Microphone(device_index=mic_index) as source:
            if prompt:
                print(prompt)
            print("(Listening... say your command)", end=" ", flush=True)
            
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=timeout)
            
        return recognizer.recognize_google(audio).lower()
    except Exception as e:
        if "wait_timeout" in str(e):
            print("⏰ Timeout - Didn't hear anything")
        elif "UnknownValueError" in str(e):
            print("🔇 Couldn't understand audio")
        else:
            print(f"❌ Error: {e}")
        return None

def process_command(command):
    """Process voice commands for lights and doors"""
    if not command:
        return
        
    print(f"\n✅ You said: {command}")
    
    # Process light commands
    if "all on" in command:
        set_all_lights("on")
    elif "all off" in command:
        set_all_lights("off")
    else:
        for i in range(1, 5):
            if f"l{i} on" in command or f"light {i} on" in command:
                set_light(i, "on")
            elif f"l{i} off" in command or f"light {i} off" in command:
                set_light(i, "off")
    
    # Process door commands
    if "all open" in command:
        set_all_doors("open")
    elif "all close" in command:
        set_all_doors("close")
    else:
        for i in range(1, 4):
            if f"d{i} open" in command or f"door {i} open" in command:
                set_door(i, "open")
            elif f"d{i} close" in command or f"door {i} close" in command:
                set_door(i, "close")
            elif "open" in command and f"door {i}" in command:
                set_door(i, "open")
            elif "close" in command and f"door {i}" in command:
                set_door(i, "close")

if __name__ == "__main__":
    print("\n🏠 Raspberry Pi Voice Control System")
    print("----------------------------------")
    print("Available commands:")
    print("  - Individual lights: 'L1 ON', 'L2 OFF', 'LIGHT 3 ON', etc.")
    print("  - All lights: 'ALL ON', 'ALL OFF'")
    print("  - Individual doors: 'D1 OPEN', 'DOOR 2 CLOSE', etc.")
    print("  - All doors: 'ALL OPEN', 'ALL CLOSE'")
    print("Press Ctrl+C to exit\n")
    
    try:
        # Initialize all doors to closed position
        set_all_doors("close")
        
        while True:
            command = listen_for_command("\n🎤 Say a command:")
            process_command(command)
    except KeyboardInterrupt:
        print("\n👋 System shutting down...")
    finally:
        # Cleanup
        d1_servo.stop()
        d2_servo.stop()
        d3_servo.stop()
        GPIO.cleanup()
        print("✅ GPIO cleanup complete")