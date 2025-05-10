from speech_recognition import Recognizer, Microphone
import time
import os
import RPi.GPIO as GPIO

# GPIO Setup
L1_PIN = 17       # GPIO pin for light
SERVO_PIN = 18    # GPIO pin for door servo
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Initialize outputs
GPIO.setup(L1_PIN, GPIO.OUT)
GPIO.output(L1_PIN, GPIO.LOW)

# Servo motor setup (for door)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)  # 50Hz PWM frequency
servo.start(0)  # Initialize servo

# Door states
DOOR_OPEN = False

def set_door(position):
    """Control servo to open/close door"""
    global DOOR_OPEN
    if position == "open":
        servo.ChangeDutyCycle(7.5)  # 90 degrees (open position)
        DOOR_OPEN = True
        print("🚪 Door opened")
    elif position == "close":
        servo.ChangeDutyCycle(2.5)  # 0 degrees (closed position)
        DOOR_OPEN = False
        print("🚪 Door closed")
    time.sleep(1)  # Give servo time to move
    servo.ChangeDutyCycle(0)  # Stop sending signal

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
    """Process voice commands for both light and door"""
    if command:
        print(f"\n✅ You said: {command}")
        
        # Light control
        if "l1 on" in command:
            GPIO.output(L1_PIN, GPIO.HIGH)
            print("💡 Light L1 turned ON")
        elif "l1 off" in command:
            GPIO.output(L1_PIN, GPIO.LOW)
            print("💡 Light L1 turned OFF")
            
        # Door control
        elif "d1 open" in command:
            set_door("open")
        elif "d1 close" in command:
            set_door("close")
        elif "door" in command and ("open" in command or "close" in command):
            action = "open" if "open" in command else "close"
            set_door(action)
        else:
            print("⚠️ Unknown command. Try 'L1 ON/OFF' or 'D1 OPEN/CLOSE'")

if __name__ == "__main__":
    print("\n🏠 Raspberry Pi Voice Control System")
    print("----------------------------------")
    print("Available commands:")
    print("  - Light: 'L1 ON', 'L1 OFF'")
    print("  - Door: 'D1 OPEN', 'D1 CLOSE'")
    print("Press Ctrl+C to exit\n")
    
    try:
        # Initialize door to closed position
        set_door("close")
        
        while True:
            command = listen_for_command("\n🎤 Say a command:")
            process_command(command)
    except KeyboardInterrupt:
        print("\n👋 System shutting down...")
    finally:
        # Cleanup
        servo.stop()
        GPIO.cleanup()
        print("✅ GPIO cleanup complete")