'''
test Cases :

1. Tests the case where the external MQTT client is connected (is_connected returns True) and the publish method succeeds (rc == 0).
Expected result: The function returns True.
test_publish_intent_external_failure_not_connected:

2. Tests the case where the external MQTT client is not connected (is_connected returns False).
Expected result: The function returns False.
test_publish_intent_external_failure_publish_error:

3. Tests the case where the external MQTT client is connected (is_connected returns True), but the publish method fails (rc != 0).
Expected result: The function returns False.
test_publish_intent_external_invalid_confidence:

4. Tests the case where the confidence parameter is invalid (e.g., a string instead of a numeric value). However, the function does not validate the confidence type, so it proceeds to publish the message.
Expected result: The function returns True (assuming publish succeeds).
test_publish_intent_external_empty_intent_name:

5. Tests the case where the intent_name parameter is an empty string. The function does not validate the intent_name, so it proceeds to publish the message.
Expected result: The function returns True (assuming publish succeeds).
test_publish_intent_external_null_client:

6. Tests the case where the external_mqtt_client is None.
Expected result: The function returns False.'''

import unittest
from unittest.mock import MagicMock
import json
import sys
import os
import io

# Add parent folder to path so "rhasspy" package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from rhasspy_voice import voiceControl

class TestPublishIntentExternal(unittest.TestCase):
    def setUp(self):
        self.mock_mqtt_client = MagicMock()
        voiceControl.external_mqtt_client = self.mock_mqtt_client
        self._suppress_output()

    def tearDown(self):
        self._restore_output()

    def _suppress_output(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

    def _restore_output(self):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

    def test_publish_intent_external_success(self):
        self.mock_mqtt_client.is_connected.return_value = True
        self.mock_mqtt_client.publish.return_value.rc = 0
        # Create a sample payload dictionary
        sample_payload = {"name": "TestDevice", "state": "on"}
        result = voiceControl.publish_intent_external(
            topic="test/topic", payload_dict=sample_payload)
        self.assertTrue(result)
        self.mock_mqtt_client.publish.assert_called_once_with("test/topic", json.dumps(sample_payload))

    def test_publish_intent_external_failure_not_connected(self):
        self.mock_mqtt_client.is_connected.return_value = False
        sample_payload = {"name": "TestDevice", "state": "on"}
        result = voiceControl.publish_intent_external(
            topic="test/topic", payload_dict=sample_payload)
        self.assertFalse(result)

    def test_publish_intent_external_failure_publish_error(self):
        self.mock_mqtt_client.is_connected.return_value = True
        self.mock_mqtt_client.publish.return_value.rc = 1
        sample_payload = {"name": "TestDevice", "state": "on"}
        result = voiceControl.publish_intent_external(
            topic="test/topic", payload_dict=sample_payload)
        self.assertFalse(result)

    # This test case might need re-evaluation.
    # The function now takes a dict; "invalid confidence" isn't directly applicable
    # unless it's part of the payload_dict structure you expect.
    # For now, let's assume a valid payload structure.
    def test_publish_intent_external_valid_payload_structure(self):
        self.mock_mqtt_client.is_connected.return_value = True
        self.mock_mqtt_client.publish.return_value.rc = 0
        # Example of a payload that might have come from parse_rhasspy_intent
        valid_payload = {"name": "l1", "state": "on"}
        result = voiceControl.publish_intent_external(
            topic="test/topic", payload_dict=valid_payload)
        self.assertTrue(result)
        self.mock_mqtt_client.publish.assert_called_once_with("test/topic", json.dumps(valid_payload))


    # This test case also needs re-evaluation.
    # An "empty intent name" would mean parse_rhasspy_intent might return None or a specific dict.
    # If parse_rhasspy_intent returns None, publish_intent_external wouldn't even be called.
    # Let's test with a payload that might represent an "empty" or "default" mapping if one exists.
    # Or, more simply, just ensure it handles a generic dictionary.
    def test_publish_intent_external_generic_payload(self):
        self.mock_mqtt_client.is_connected.return_value = True
        self.mock_mqtt_client.publish.return_value.rc = 0
        generic_payload = {"device_id": "unknown", "action": "none"} # Example
        result = voiceControl.publish_intent_external(
            topic="test/topic", payload_dict=generic_payload)
        self.assertTrue(result)
        self.mock_mqtt_client.publish.assert_called_once_with("test/topic", json.dumps(generic_payload))


    def test_publish_intent_external_null_client(self):
        voiceControl.external_mqtt_client = None
        sample_payload = {"name": "TestDevice", "state": "on"}
        result = voiceControl.publish_intent_external(
            topic="test/topic", payload_dict=sample_payload)
        self.assertFalse(result)

if __name__ == "__main__":
    class CustomTestResult(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test)
            print(f"PASS: {test._testMethodName}")

        def addFailure(self, test, err):
            super().addFailure(test, err)
            print(f"FAIL: {test._testMethodName}")

        def addError(self, test, err):
            super().addError(test, err)
            print(f"ERROR: {test._testMethodName}")

    runner = unittest.TextTestRunner(resultclass=CustomTestResult, verbosity=0)
    unittest.main(testRunner=runner)
