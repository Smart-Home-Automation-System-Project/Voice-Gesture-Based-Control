import speech_recognition as sr
import os
import time

# Optional: Suppress ALSA/JACK warnings (can be noisy on Linux)
# Note: This might hide important audio system errors.
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'
os.environ['PA_ALSA_PLUGHW_IGNORE'] = '1' # May help with some ALSA issues

def find_microphone_index():
    """
    Lists available microphones and attempts to select the best one.
    Prioritizes PulseAudio, then looks for 'analog' or 'input' in the name.
    Falls back to the default device (index 0) if no preferred device is found.
    """
    print("Searching for microphones...")
    available_mics = sr.Microphone.list_microphone_names()
    print("Available Microphones:")
    for i, name in enumerate(available_mics):
        print(f"  [{i}] {name}")

    # Try to find PulseAudio first
    for i, name in enumerate(available_mics):
        if "pulse" in name.lower():
            print(f"\n🔊 Selecting PulseAudio device: [{i}] {name}")
            return i

    # Fallback: Try to find an analog input device
    for i, name in enumerate(available_mics):
        if "analog" in name.lower() or "input" in name.lower():
            print(f"\n🔊 Selecting Analog device: [{i}] {name}")
            return i

    # If no preferred device found, use the default
    print("\n⚠️ No preferred microphone (PulseAudio/Analog) found. Using default [0].")
    if available_mics:
         print(f"   Default device: {available_mics[0]}")
         return 0
    else:
        print("\n❌ ERROR: No microphones found!")
        return None

def listen_for_voice_command(recognizer, microphone, mic_index):
    """
    Listens for a voice command using the specified microphone and recognizer.
    Handles ambient noise adjustment and speech recognition.
    """
    if mic_index is None:
        print("❌ Cannot listen: No microphone index provided.")
        return None

    try:
        with microphone(device_index=mic_index) as source:
            #print("\nAdjusting for ambient noise... Please wait.")
            #recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Listening... (Speak clearly)")
            # Add a short beep sound (optional, requires system support for '\a')
            # print('\a', end='', flush=True)
            try:
                # Listen for audio input with timeouts
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                print("👂 No speech detected within the timeout.")
                return None
        print("🧠 Processing audio...")
        try:
            # Recognize speech using Google Web Speech API
            command = recognizer.recognize_google(audio)
            print(f"✅ Recognized: '{command}'")
            return command.lower()
        except sr.UnknownValueError:
            print("❓ Google Speech Recognition could not understand audio.")
            return None
        except sr.RequestError as e:
            print(f"📡 Could not request results from Google Speech Recognition service; {e}")
            return None

    except Exception as e:
        print(f"❌ An unexpected error occurred during listening: {e}")
        # Specific check if microphone access failed
        if "Invalid input device" in str(e):
             print("   Hint: Check if the selected microphone index is correct and accessible.")
        return None

def main():
    """
    Main function to run the voice listener loop.
    """
    print("\n--- Voice Command Listener ---")
    print("Initializing...")

    recognizer = sr.Recognizer()
    microphone = sr.Microphone

    # Find the microphone index once at the start
    mic_index = find_microphone_index()
    if mic_index is None:
        print("\nExiting due to microphone issues.")
        return

    print("\nReady to listen. Press Ctrl+C to exit.")

    try:
        while True:
            command = listen_for_voice_command(recognizer, microphone, mic_index)
            if command:
                # --- Add your command processing logic here ---
                print(f"➡️ Processing command: '{command}'")
                if "hello" in command:
                    print("   -> Hello to you too!")
                # Add more elif conditions for other commands
                # ---------------------------------------------
            else:
                print("   (No command processed)")

            # Optional: Add a small delay to prevent high CPU usage in the loop
            # time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n👋 Ctrl+C detected. Shutting down gracefully.")
    except Exception as e:
        print(f"\n💥 An unexpected error occurred in the main loop: {e}")
    finally:
        print("--- Listener Stopped ---")

if __name__ == "__main__":
    # Ensure you are in your virtual environment (.venv)
    # Run with: python3 ... .py
    main()