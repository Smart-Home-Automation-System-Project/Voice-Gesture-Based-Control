'''from speech_recognition import Recognizer, Microphone

r = Recognizer()
mic = Microphone()

print("Speak now...")
with mic as source:
    audio = r.listen(source)

try:
    print("You said:", r.recognize_google(audio))
except Exception as e:
    print("Error:", e)'''

from speech_recognition import Recognizer, Microphone
import time

def listen_for_command(prompt=None, timeout=3):
    recognizer = Recognizer()
    microphone = Microphone()
    
    try:
        with microphone as source:
            if prompt:
                print(prompt)
            print("(Speak after the beep)", end=" ", flush=True)
            print("\a")  # System beep
            
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
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

def main():
    print("\n🎤 Voice Command System")
    print("----------------------")
    print("1. Say 'turn left' → Output: 1")
    print("2. Answer yes/no by voice\n")
    time.sleep(1)
    
    while True:
        # Listen for main command
        command = listen_for_command("\n💬 Say 'turn left':", timeout=3)
        
        if command:
            if "turn left" in command:
                print("\n✅ Output: 1")
            else:
                print(f"\n🔍 Heard: '{command}' (Expected 'turn left')")
        
        # Voice confirmation
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
    main()