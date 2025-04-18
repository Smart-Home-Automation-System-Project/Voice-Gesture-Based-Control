from speech_recognition import Recognizer, Microphone
import time
import os
import RPi.GPIO as GPIO  # For Raspberry Pi GPIO control

# GPIO setup
L1_PIN = 17  # Change this to the GPIO pin you're using for L1
GPIO.setmode(GPIO.BCM)
GPIO.setup(L1_PIN, GPIO.OUT)
GPIO.output(L1_PIN, GPIO.LOW)  # Start with light off

def get_microphone_index():
    """Try to find the correct microphone index"""
    try:
        # List all microphones
        print("Available microphones:")
        for index, name in enumerate(Microphone.list_microphone_names()):
            print(f"{index}: {name}")
            
        # Try to find the analog input (usually the built-in mic)
        for index, name in enumerate(Microphone.list_microphone_names()):
            if "analog" in name.lower() or "input" in name.lower():
                print(f"\n🔊 Selecting microphone: {name} (index {index})")
                return index
                
        print("\n⚠️ Couldn't find analog input, using default (index 0)")
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
            print("(Speak after the beep)", end=" ", flush=True)
            # Simple beep alternative
            print("\a", end="", flush=True)
            
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
    """Process the voice command and control the light"""
    if command:
        print(f"\n✅ You said: {command}")
        
        if "l1 on" in command:
            GPIO.output(L1_PIN, GPIO.HIGH)
            print("💡 Light L1 turned ON")
        elif "l1 off" in command:
            GPIO.output(L1_PIN, GPIO.LOW)
            print("💡 Light L1 turned OFF")
        else:
            print("⚠️ Unknown command. Try 'L1 ON' or 'L1 OFF'")

if __name__ == "__main__":
    print("\n🎤 Raspberry Pi Voice Control System")
    print("--------------------------------")
    print("Available commands: 'L1 ON', 'L1 OFF'")
    print("Note: Make sure your microphone is properly configured")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            command = listen_for_command("\n💬 Say a command (L1 ON/OFF):")
            process_command(command)
    except KeyboardInterrupt:
        print("\n👋 Program terminated by user")
    finally:
        GPIO.cleanup()  # Clean up GPIO on exit