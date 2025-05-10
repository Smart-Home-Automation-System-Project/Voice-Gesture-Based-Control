import sys
import os
from unittest.mock import MagicMock, patch
import unittest

# Add the parent directory to sys.path to enable import of the rhasspy package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import the mqtt_subscriber module from the rhasspy package
from rhasspy_voice.mqtt_subscriber import on_connect

class TestMQTTSubscriber(unittest.TestCase):

    @patch("rhasspy_voice.mqtt_subscriber.TOPICS", ["test/topic1", "test/topic2"])
    def test_on_connect_success(self):
        # Mock the MQTT client
        mock_client = MagicMock()
        userdata = None
        flags = {}
        reason_code = 0  # Success code
        properties = None

        # Call the on_connect function
        on_connect(mock_client, userdata, flags, reason_code, properties)

        # Verify that the client subscribed to the topics
        mock_client.subscribe.assert_any_call("test/topic1")
        mock_client.subscribe.assert_any_call("test/topic2")
        self.assertEqual(mock_client.subscribe.call_count, 2)

    def test_on_connect_failure(self):
        # Mock the MQTT client
        mock_client = MagicMock()
        userdata = None
        flags = {}
        reason_code = 1  # Simulate a connection failure
        properties = None

        # Call the on_connect function and patch the print function
        with patch("builtins.print") as mock_print:
            on_connect(mock_client, userdata, flags, reason_code, properties)

            # Verify that the failure message was printed
            mock_print.assert_called_once_with("Connection failed, reason code 1")

if __name__ == "__main__":
    unittest.main()
