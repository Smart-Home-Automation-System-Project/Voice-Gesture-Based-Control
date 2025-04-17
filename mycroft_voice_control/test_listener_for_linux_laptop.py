from speech_recognition import Recognizer, Microphone, UnknownValueError, RequestError, WaitTimeoutError
import time
import os
import sys

def system_beep():
    """Cross-platform beep sound"""
    try:
        os.system('echo -n "\a"; sleep 0.2')
    except:
        print("\a", end='', flush=True)

def get_microphone_index():
    """Find the correct microphone index"""
    recognizer = Recognizer()
    print("\nAvailable microphones:")
    for index, name in enumerate(Microphone.list_microphone_names()):
        print(f"{index}: {name}")
    
    # Try to find a suitable microphone automatically
    for index, name in enumerate(Microphone.list_microphone_names()):
        if 'input' in name.lower() or 'mic' in name.lower():
            print(f"\nAuto-selected microphone: {index} - {name}")
            return index
    
    # Fallback to default
    print("\nUsing default microphone (index 0)")
    return 0

def listen_for_command(prompt=None, timeout=3):
    recognizer = Recognizer()
    mic_index = get_microphone_index()
    
    try:
        with Microphone(device_index=mic_index) as source:
            if prompt:
                print(prompt)
            print("(Speak after the beep)", end=" ", flush=True)
            system_beep()
            
            # Longer adjustment for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print("\n🎤 Listening...", end=" ", flush=True)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=timeout)
            
        try:
            result = recognizer.recognize_google(audio).lower()
            print(f"Heard: '{result}'")
            return result
        except UnknownValueError:
            print("🔇 Couldn't understand audio")
            return None
        except RequestError as e:
            print(f"🌐 Network error: {e}")
            return None
            
    except WaitTimeoutError:
        print("⏰ Timeout - Didn't hear anything")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def main():
    print("\n🎤 Voice Command System")
    print("----------------------")
    print("1. Say 'turn left' → Output: 1")
    print("2. Answer yes/no by voice\n")
    time.sleep(1)
    
    while True:
        command = listen_for_command("\n💬 Say 'turn left':", timeout=3)
        
        if command:
            if "turn left" in command:
                print("\n✅ Output: 1")
            else:
                print(f"\n🔍 Heard: '{command}' (Expected 'turn left')")
        
        while True:
            response = listen_for_command("\n🗣️ Continue? Say 'yes' or 'no':", timeout=2)
            
            if not response:
                print("Please try answering again")
                continue
                
            if "no" in response:
                print("\n👋 Goodbye!")
                return
            elif "yes" in response:
                print("\n🔄 Restarting...")
                break
            else:
                print(f"❓ Unclear response: '{response}'. Please say 'yes' or 'no'")

if __name__ == "__main__":
    # Check dependencies
    try:
        import speech_recognition as sr
        import pyaudio
    except ImportError as e:
        print("Missing dependencies. Please run:")
        print("sudo apt install python3-pip portaudio19-dev python3-pyaudio")
        print("pip3 install SpeechRecognition pyaudio")
        sys.exit(1)
    
    # Verify microphone access
    try:
        p = pyaudio.PyAudio()
        print("\nAudio System Info:")
        print(f"ALSA Version: {p.get_host_api_info_by_index(0).get('name')}")
        print("Available devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            print(f"{i}: {info['name']} (Input channels: {info['maxInputChannels']})")
        p.terminate()
    except Exception as e:
        print(f"⚠️ Microphone access error: {e}")
        print("Try these fixes:")
        print("1. Make sure microphone is not muted in system settings")
        print("2. Run: sudo apt install libasound2-dev")
        print("3. Check permissions with: ls -l /dev/snd/")
        sys.exit(1)
    
    main()