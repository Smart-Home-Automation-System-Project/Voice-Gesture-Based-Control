import sys
import os
import multiprocessing
import time

# Adjust sys.path to allow importing from subdirectories
# Assuming main.py is in Rhasspy0.1 and other scripts are in subfolders
sys.path.append(os.path.join(os.path.dirname(__file__), "gestureControl"))
sys.path.append(os.path.join(os.path.dirname(__file__), "rhasspy_voice"))

# Import the main functions from your scripts
# gesture_mqtt.py should have a main() function
# voiceControl.py now has run_voice_control_system()
try:
    from gesture_mqtt import main as run_gesture_control_system
    from voiceControl import run_voice_control_system
except ImportError as e:
    print(f"Error importing control modules: {e}")
    print("Please ensure gesture_mqtt.py and voiceControl.py are in their respective subdirectories (gestureControl, rhasspy_voice) and are correctly structured.")
    sys.exit(1)

def start_gesture_control():
    print("Starting Gesture Control System...")
    try:
        run_gesture_control_system()
    except Exception as e:
        print(f"Error in Gesture Control System: {e}")

def start_voice_control():
    print("Starting Voice Control System...")
    try:
        run_voice_control_system()
    except Exception as e:
        print(f"Error in Voice Control System: {e}")

if __name__ == "__main__":
    print("Smart Home Control System")
    print("Select control mode:")
    print("1. Gesture Control")
    print("2. Voice Control")
    print("3. Both (Gesture and Voice)")

    choice = ""
    while True:
        choice = input("Enter choice (1, 2, or 3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")

    gesture_process = None
    voice_process = None

    try:
        if choice == '1':
            print("Launching Gesture Control...")
            # Run in the current process for simplicity if only one is chosen
            start_gesture_control()
        elif choice == '2':
            print("Launching Voice Control...")
            # Run in the current process
            start_voice_control()
        elif choice == '3':
            print("Launching Both Gesture and Voice Control Systems...")
            gesture_process = multiprocessing.Process(target=start_gesture_control, name="GestureControl")
            voice_process = multiprocessing.Process(target=start_voice_control, name="VoiceControl")

            gesture_process.start()
            print("Gesture control process started.")
            voice_process.start()
            print("Voice control process started.")

            # Keep the main script alive while processes run
            # You might want more sophisticated process management here
            while True:
                time.sleep(1)
                if gesture_process and not gesture_process.is_alive():
                    print("Gesture control process has terminated.")
                    gesture_process.join() # Clean up
                    gesture_process = None
                if voice_process and not voice_process.is_alive():
                    print("Voice control process has terminated.")
                    voice_process.join() # Clean up
                    voice_process = None
                if not gesture_process and not voice_process and choice == '3': # Both were started and now both are done
                    print("Both control processes have finished.")
                    break
                if (not gesture_process and choice == '1') or (not voice_process and choice == '2'): # Single process finished
                    break


    except KeyboardInterrupt:
        print("\nMain script interrupted by user. Stopping processes...")
    except Exception as e:
        print(f"An error occurred in main.py: {e}")
    finally:
        if gesture_process and gesture_process.is_alive():
            print("Terminating gesture control process...")
            gesture_process.terminate()
            gesture_process.join(timeout=5) # Wait for termination
        if voice_process and voice_process.is_alive():
            print("Terminating voice control process...")
            voice_process.terminate()
            voice_process.join(timeout=5) # Wait for termination
        print("Smart Home Control System shutdown complete.")