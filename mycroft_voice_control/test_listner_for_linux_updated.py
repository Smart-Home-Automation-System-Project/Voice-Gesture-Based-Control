import os
import wave
import tempfile
import sounddevice as sd
import numpy as np
from speech_recognition import Recognizer, AudioFile
import speech_recognition as sr  # Needed for exception handling

def record_audio(duration=3, sample_rate=16000):
    """Record audio using sounddevice and return as numpy array"""
    print("\nSpeak now (waiting for voice)...", end=" ", flush=True)
    audio = sd.rec(int(duration * sample_rate),
                  samplerate=sample_rate,
                  channels=1,
                  dtype='int16')
    sd.wait()  # Wait until recording is finished
    return audio.flatten()

def save_wav(audio, sample_rate=16000):
    """Save numpy array as temporary WAV file"""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmpfile:
        with wave.open(tmpfile.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        return tmpfile.name

def listen_for_command():
    recognizer = Recognizer()
    
    try:
        # Record audio
        audio_data = record_audio()
        
        # Save to temporary WAV file
        wav_file = save_wav(audio_data)
        
        # Recognize the audio
        with AudioFile(wav_file) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio).lower()
            print(f"\nYou said: {text}")
            return text
            
    except sr.UnknownValueError:
        print("\nCouldn't understand audio")
    except sr.RequestError as e:
        print(f"\nAPI unavailable: {e}")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        if 'wav_file' in locals() and os.path.exists(wav_file):
            os.unlink(wav_file)
    return None

if __name__ == "__main__":
    print("Voice Command Listener - Speak after the prompt")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            listen_for_command()
    except KeyboardInterrupt:
        print("\nGoodbye!")