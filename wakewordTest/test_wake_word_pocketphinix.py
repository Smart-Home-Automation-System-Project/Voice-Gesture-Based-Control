from pocketsphinx import LiveSpeech

for phrase in LiveSpeech(keyphrase="jarvis", kws_threshold=1e-45): #20
    print("Wake word detected!:", phrase)