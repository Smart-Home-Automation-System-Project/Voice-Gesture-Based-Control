import sys
import os
from unittest.mock import patch, MagicMock
import unittest
import numpy as np  # Import NumPy to create mock images

# Add the parent directory of 'gestureControl' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gestureControl.door_mqtt import main

class TestDoorMQTT(unittest.TestCase):

    def test_main_mqtt_connection(self):
        with patch('gestureControl.door_mqtt.mqtt.Client') as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.is_connected.return_value = True

            with patch('gestureControl.door_mqtt.cv2.VideoCapture') as MockVideoCapture:
                mock_video_instance = MockVideoCapture.return_value
                mock_video_instance.isOpened.side_effect = [True, False]  # Simulate one loop iteration
                # Return a valid black image (480x640 with 3 color channels)
                mock_video_instance.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))

                with patch('gestureControl.door_mqtt.cv2.imshow'), \
                     patch('gestureControl.door_mqtt.cv2.waitKey', return_value=27):  # Simulate ESC key press
                    main()

            # Verify that the MQTT client methods were called
            mock_client_instance.connect.assert_called_once()
            mock_client_instance.loop_start.assert_called_once()
            mock_client_instance.loop_stop.assert_called_once()
            mock_client_instance.disconnect.assert_called_once()

    def test_main_video_capture_failure(self):
        with patch('gestureControl.door_mqtt.cv2.VideoCapture') as MockVideoCapture:
            mock_video_instance = MockVideoCapture.return_value
            mock_video_instance.isOpened.return_value = True
            mock_video_instance.read.return_value = (False, None)  # Simulate video capture failure

            with patch('gestureControl.door_mqtt.cv2.imshow'), \
                 patch('gestureControl.door_mqtt.cv2.waitKey', return_value=27):  # Simulate ESC key press
                main()

            # Verify that the video capture instance was released
            mock_video_instance.release.assert_called_once()

    def test_main_debug_toggle(self):
        with patch('gestureControl.door_mqtt.cv2.VideoCapture') as MockVideoCapture:
            mock_video_instance = MockVideoCapture.return_value
            mock_video_instance.isOpened.side_effect = [True, False]  # Simulate one loop iteration
            # Return a valid black image (480x640 with 3 color channels)
            mock_video_instance.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))

            with patch('gestureControl.door_mqtt.cv2.imshow'), \
                 patch('gestureControl.door_mqtt.cv2.waitKey', side_effect=[ord('d'), 27]):  # Simulate 'D' key press and ESC
                main()

            # Verify that the video capture instance was released
            mock_video_instance.release.assert_called_once()

if __name__ == '__main__':
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

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestDoorMQTT)
    CustomTestRunner(verbosity=0).run(suite)
