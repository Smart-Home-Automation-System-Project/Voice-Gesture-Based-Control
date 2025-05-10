from speech_recognition import Recognizer, Microphone
import time
import os

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

if __name__ == "__main__":
    print("\n🎤 Linux Voice Command System")
    print("--------------------------")
    print("Note: Make sure your microphone is properly configured")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            command = listen_for_command("\n💬 Say something:")
            if command:
                print(f"\n✅ You said: {command}")
    except KeyboardInterrupt:
        print("\n👋 Program terminated by user")