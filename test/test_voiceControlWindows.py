import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import voiceControlWindows 
import io
import json

class TestVoiceControlWindows(unittest.TestCase):

    @patch('voiceControlWindows.pyaudio.PyAudio')
    def test_record_audio_success(self, mock_pyaudio):
        mock_stream = MagicMock()
        mock_stream.read.return_value = b'\x00\x01' * 1024
        mock_p = MagicMock()
        mock_p.open.return_value = mock_stream
        mock_pyaudio.return_value = mock_p

        result = voiceControlWindows.record_audio(1, 16000, 1)
        self.assertIsInstance(result, bytes)

    @patch('voiceControlWindows.requests.post')
    def test_get_text_from_audio_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Turn on the lights"
        mock_post.return_value = mock_response

        dummy_audio = b'RIFF....WAVEfmt '  # Minimal WAV header
        result = voiceControlWindows.get_text_from_audio(dummy_audio)
        self.assertEqual(result, "Turn on the lights")

    @patch('voiceControlWindows.requests.post')
    def test_get_intent_from_text_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "intent": {"name": "TurnOnLights", "confidence": 0.95}
        }
        mock_post.return_value = mock_response

        result = voiceControlWindows.get_intent_from_text("Turn on the lights")
        self.assertIn("intent", result)
        self.assertEqual(result["intent"]["name"], "TurnOnLights")

    def test_publish_intent_external_success(self):
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_publish_result = MagicMock()
        mock_publish_result.rc = 0
        mock_client.publish.return_value = mock_publish_result

        voiceControlWindows.external_mqtt_client = mock_client
        success = voiceControlWindows.publish_intent_external(
            "rhasspy/intent/recognized", "TestIntent", 0.9
        )
        self.assertTrue(success)

    def test_publish_intent_external_failure(self):
        mock_client = MagicMock()
        mock_client.is_connected.return_value = False

        voiceControlWindows.external_mqtt_client = mock_client
        success = voiceControlWindows.publish_intent_external(
            "rhasspy/intent/recognized", "TestIntent", 0.9
        )
        self.assertFalse(success)


if __name__ == '__main__':
    unittest.main()
