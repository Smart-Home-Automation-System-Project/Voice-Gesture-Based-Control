import unittest
from unittest.mock import MagicMock
import json
import sys
import os
import io

# Add the parent directory to the Python path to resolve the ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import voiceControl

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
        result = voiceControl.publish_intent_external(
            topic="test/topic", intent_name="TestIntent", confidence=0.95)
        self.assertTrue(result)

    def test_publish_intent_external_failure_not_connected(self):
        self.mock_mqtt_client.is_connected.return_value = False
        result = voiceControl.publish_intent_external(
            topic="test/topic", intent_name="TestIntent", confidence=0.95)
        self.assertFalse(result)

    def test_publish_intent_external_failure_publish_error(self):
        self.mock_mqtt_client.is_connected.return_value = True
        self.mock_mqtt_client.publish.return_value.rc = 1
        result = voiceControl.publish_intent_external(
            topic="test/topic", intent_name="TestIntent", confidence=0.95)
        self.assertFalse(result)

    def test_publish_intent_external_invalid_confidence(self):
        self.mock_mqtt_client.is_connected.return_value = True
        self.mock_mqtt_client.publish.return_value.rc = 0
        result = voiceControl.publish_intent_external(
            topic="test/topic", intent_name="TestIntent", confidence="invalid_confidence")
        self.assertTrue(result)

    def test_publish_intent_external_empty_intent_name(self):
        self.mock_mqtt_client.is_connected.return_value = True
        self.mock_mqtt_client.publish.return_value.rc = 0
        result = voiceControl.publish_intent_external(
            topic="test/topic", intent_name="", confidence=0.95)
        self.assertTrue(result)

    def test_publish_intent_external_null_client(self):
        voiceControl.external_mqtt_client = None
        result = voiceControl.publish_intent_external(
            topic="test/topic", intent_name="TestIntent", confidence=0.95)
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