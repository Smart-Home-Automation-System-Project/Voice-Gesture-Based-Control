import unittest
from unittest.mock import patch, MagicMock
import json
import sys

# Assuming the functions to be tested are imported from the main script
# from your_script import (
#     record_audio,
#     get_text_from_audio,
#     get_intent_from_text,
#     publish_intent,
#     mqtt_client,
# )

class TestSmartHomeSystem(unittest.TestCase):
    
    # Test the audio recording functionality
    @patch('sounddevice.rec')
    @patch('sounddevice.wait')
    def test_record_audio(self, mock_wait, mock_rec):
        # Simulate recording audio
        mock_rec.return_value = b"fake_audio_data"
        mock_wait.return_value = None
        result = record_audio(5, 16000, 1)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), len(b"fake_audio_data"))
    
    # Test sending audio to Rhasspy STT
    @patch('requests.post')
    def test_get_text_from_audio(self, mock_post):
        # Simulate a successful STT request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Turn on the lights"
        mock_post.return_value = mock_response
        
        audio_data = b"fake_audio_data"
        result = get_text_from_audio(audio_data)
        self.assertEqual(result, "Turn on the lights")
    
    # Test handling of STT request failure
    @patch('requests.post')
    def test_get_text_from_audio_failure(self, mock_post):
        # Simulate an error in STT request
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        audio_data = b"fake_audio_data"
        result = get_text_from_audio(audio_data)
        self.assertIsNone(result)
    
    # Test intent recognition from text
    @patch('requests.post')
    def test_get_intent_from_text(self, mock_post):
        # Simulate a successful NLU request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "intent": {"name": "TurnOnLights", "confidence": 0.95}
        }
        mock_post.return_value = mock_response
        
        text = "turn on the lights"
        result = get_intent_from_text(text)
        self.assertEqual(result['intent']['name'], 'TurnOnLights')
        self.assertEqual(result['intent']['confidence'], 0.95)
    
    # Test handling of NLU request failure
    @patch('requests.post')
    def test_get_intent_from_text_failure(self, mock_post):
        # Simulate an error in NLU request
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        text = "turn on the lights"
        result = get_intent_from_text(text)
        self.assertIsNone(result)
    
    # Test MQTT publish intent
    @patch('paho.mqtt.client.Client.publish')
    def test_publish_intent(self, mock_publish):
        # Simulate a successful MQTT publish
        mock_publish.return_value.rc = 0  # MQTT_ERR_SUCCESS
        intent_name = "TurnOnLights"
        confidence = 0.95
        
        # Initialize MQTT client before publishing
        mqtt_client = MagicMock()
        mqtt_client.is_connected.return_value = True
        result = publish_intent("rhasspy/intent/recognized", intent_name, confidence)
        
        # Verify that publish was called
        mock_publish.assert_called_once_with("rhasspy/intent/recognized", json.dumps({
            "intent": intent_name,
            "confidence": confidence
        }))
        self.assertEqual(result.rc, 0)
    
    # Test MQTT client not connected
    @patch('paho.mqtt.client.Client.publish')
    def test_publish_intent_not_connected(self, mock_publish):
        # Simulate MQTT client not being connected
        mqtt_client = MagicMock()
        mqtt_client.is_connected.return_value = False
        
        result = publish_intent("rhasspy/intent/recognized", "TurnOnLights", 0.95)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
