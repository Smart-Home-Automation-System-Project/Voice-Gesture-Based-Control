import unittest
from unittest.mock import MagicMock
import sys
import os

# Add gestureControl folder to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from gestureControl.mqtt_listener import on_connect

class TestOnConnect(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()

    def test_on_connect_success(self):
        rc = 0
        on_connect(self.mock_client, None, None, rc, None)
        self.mock_client.subscribe.assert_called_once_with("home/automation/Door1_control")

    def test_on_connect_failure(self):
        rc = 1
        on_connect(self.mock_client, None, None, rc, None)
        self.mock_client.subscribe.assert_not_called()

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

    class CustomTestRunner(unittest.TextTestRunner):
        resultclass = CustomTestResult

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestOnConnect)
    CustomTestRunner(verbosity=0).run(suite)
