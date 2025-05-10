'''
test cases :
1	The system sends a proper open/close signal to the smart door
2	The system should stop safely and release camera resources	
3	Pressing the key activates/deactivates gesture detail overlay	
4	Test detection of thumb up gesture with mock hand landmarks	Gesture is correctly identified as thumb up	
5   Test detection of thumb down gesture with mock hand landmarks	Gesture is correctly identified as thumb down
6   Test detection of open palm gesture with mock hand landmarks	Gesture is correctly identified as open palm
7   Test detection of number one gesture (index finger up) with mock hand landmarks	Gesture is correctly identified as number one	
8   Test detection of number two gesture (victory sign) with mock hand landmarks	Gesture is correctly identified as number two	
9   Test detection of rock on gesture (index and pinky up) with mock hand landmarks	Gesture is correctly identified as rock on
'''
import sys
import os
from unittest.mock import patch, MagicMock
import unittest
import numpy as np  # Import NumPy to create mock images

# Add the parent directory of 'gestureControl' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))

from gestureControl.gesture_control import main, is_thumb_up, is_thumb_down, is_open_palm, is_number_one, is_number_two, is_rock_on

class TestGestureMQTT(unittest.TestCase):

    def test_main_mqtt_connection(self):
        with patch('gestureControl.gesture_control.mqtt.Client') as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.is_connected.return_value = True

            with patch('gestureControl.gesture_control.cv2.VideoCapture') as MockVideoCapture:
                mock_video_instance = MockVideoCapture.return_value
                mock_video_instance.isOpened.side_effect = [True, False]  # Simulate one loop iteration
                # Return a valid black image (480x640 with 3 color channels)
                mock_video_instance.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))

                with patch('gestureControl.gesture_control.cv2.imshow'), \
                     patch('gestureControl.gesture_control.cv2.waitKey', return_value=27):  # Simulate ESC key press
                    main()

            # Verify that the MQTT client methods were called
            mock_client_instance.connect.assert_called_once()
            mock_client_instance.loop_start.assert_called_once()
            mock_client_instance.loop_stop.assert_called_once()
            mock_client_instance.disconnect.assert_called_once()

    def test_main_video_capture_failure(self):
        with patch('gestureControl.gesture_control.mqtt.Client') as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.is_connected.return_value = True

            with patch('gestureControl.gesture_control.cv2.VideoCapture') as MockVideoCapture:
                mock_video_instance = MockVideoCapture.return_value
                mock_video_instance.isOpened.return_value = True
                mock_video_instance.read.return_value = (False, None)  # Simulate video capture failure

                with patch('gestureControl.gesture_control.cv2.imshow'), \
                     patch('gestureControl.gesture_control.cv2.waitKey', return_value=27):  # Simulate ESC key press
                    main()

            # Verify that the video capture instance was released
            mock_video_instance.release.assert_called_once()

    def test_main_debug_toggle(self):
        with patch('gestureControl.gesture_control.mqtt.Client') as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.is_connected.return_value = True

            with patch('gestureControl.gesture_control.cv2.VideoCapture') as MockVideoCapture:
                mock_video_instance = MockVideoCapture.return_value
                mock_video_instance.isOpened.side_effect = [True, False]  # Simulate one loop iteration
                # Return a valid black image (480x640 with 3 color channels)
                mock_video_instance.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))

                with patch('gestureControl.gesture_control.cv2.imshow'), \
                     patch('gestureControl.gesture_control.cv2.waitKey', side_effect=[ord('d'), 27]):  # Simulate 'D' key press and ESC
                    main()

            # Verify that the video capture instance was released
            mock_video_instance.release.assert_called_once()

    def test_thumb_up_gesture(self):
        # Create a mock hand_landmarks object
        mock_landmarks = MagicMock()
        mock_landmarks.landmark = [MagicMock() for _ in range(21)]  # 21 landmarks for hand
        mock_landmarks.landmark[4].x, mock_landmarks.landmark[4].y = 0.5, 0.2  # THUMB_TIP
        mock_landmarks.landmark[2].x, mock_landmarks.landmark[2].y = 0.5, 0.4  # THUMB_MCP
        mock_landmarks.landmark[8].x, mock_landmarks.landmark[8].y = 0.5, 0.5  # INDEX_FINGER_TIP
        mock_landmarks.landmark[12].x, mock_landmarks.landmark[12].y = 0.5, 0.5  # MIDDLE_FINGER_TIP
        mock_landmarks.landmark[16].x, mock_landmarks.landmark[16].y = 0.5, 0.5  # RING_FINGER_TIP
        mock_landmarks.landmark[20].x, mock_landmarks.landmark[20].y = 0.5, 0.5  # PINKY_TIP

        # Create a mock image
        mock_image = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch('gestureControl.gesture_control.cv2.putText'):
            result = is_thumb_up(mock_landmarks, mock_image)
            self.assertTrue(result)

    def test_thumb_down_gesture(self):
        # Create a mock hand_landmarks object
        mock_landmarks = MagicMock()
        mock_landmarks.landmark = [MagicMock() for _ in range(21)]
        mock_landmarks.landmark[4].x, mock_landmarks.landmark[4].y = 0.5, 0.6  # THUMB_TIP
        mock_landmarks.landmark[2].x, mock_landmarks.landmark[2].y = 0.5, 0.4  # THUMB_MCP
        mock_landmarks.landmark[8].x, mock_landmarks.landmark[8].y = 0.5, 0.3  # INDEX_FINGER_TIP
        mock_landmarks.landmark[12].x, mock_landmarks.landmark[12].y = 0.5, 0.3  # MIDDLE_FINGER_TIP
        mock_landmarks.landmark[16].x, mock_landmarks.landmark[16].y = 0.5, 0.3  # RING_FINGER_TIP
        mock_landmarks.landmark[20].x, mock_landmarks.landmark[20].y = 0.5, 0.3  # PINKY_TIP

        # Create a mock image
        mock_image = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch('gestureControl.gesture_control.cv2.putText'):
            result = is_thumb_down(mock_landmarks, mock_image)
            self.assertTrue(result)

    def test_open_palm_gesture(self):
        # Create a mock hand_landmarks object
        mock_landmarks = MagicMock()
        mock_landmarks.landmark = [MagicMock() for _ in range(21)]
        # Fingertips lower than PIP joints
        mock_landmarks.landmark[8].x, mock_landmarks.landmark[8].y = 0.5, 0.2  # INDEX_FINGER_TIP
        mock_landmarks.landmark[6].x, mock_landmarks.landmark[6].y = 0.5, 0.4  # INDEX_FINGER_PIP
        mock_landmarks.landmark[12].x, mock_landmarks.landmark[12].y = 0.5, 0.2  # MIDDLE_FINGER_TIP
        mock_landmarks.landmark[10].x, mock_landmarks.landmark[10].y = 0.5, 0.4  # MIDDLE_FINGER_PIP
        mock_landmarks.landmark[16].x, mock_landmarks.landmark[16].y = 0.5, 0.2  # RING_FINGER_TIP
        mock_landmarks.landmark[14].x, mock_landmarks.landmark[14].y = 0.5, 0.4  # RING_FINGER_PIP
        mock_landmarks.landmark[20].x, mock_landmarks.landmark[20].y = 0.5, 0.2  # PINKY_TIP
        mock_landmarks.landmark[18].x, mock_landmarks.landmark[18].y = 0.5, 0.4  # PINKY_PIP
        # Thumb extended
        mock_landmarks.landmark[4].x, mock_landmarks.landmark[4].y = 0.7, 0.4  # THUMB_TIP
        mock_landmarks.landmark[0].x, mock_landmarks.landmark[0].y = 0.5, 0.5  # WRIST
        mock_landmarks.landmark[1].x, mock_landmarks.landmark[1].y = 0.6, 0.4  # THUMB_CMC
        mock_landmarks.landmark[3].x, mock_landmarks.landmark[3].y = 0.65, 0.4  # THUMB_IP

        # Create a mock image
        mock_image = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch('gestureControl.gesture_control.cv2.putText'):
            result = is_open_palm(mock_landmarks, mock_image)
            self.assertTrue(result)

    def test_number_one_gesture(self):
        # Create a mock hand_landmarks object
        mock_landmarks = MagicMock()
        mock_landmarks.landmark = [MagicMock() for _ in range(21)]
        # Index finger extended, others folded
        mock_landmarks.landmark[8].x, mock_landmarks.landmark[8].y = 0.5, 0.2  # INDEX_FINGER_TIP
        mock_landmarks.landmark[6].x, mock_landmarks.landmark[6].y = 0.5, 0.4  # INDEX_FINGER_PIP
        mock_landmarks.landmark[12].x, mock_landmarks.landmark[12].y = 0.5, 0.5  # MIDDLE_FINGER_TIP
        mock_landmarks.landmark[10].x, mock_landmarks.landmark[10].y = 0.5, 0.4  # MIDDLE_FINGER_PIP
        mock_landmarks.landmark[16].x, mock_landmarks.landmark[16].y = 0.5, 0.5  # RING_FINGER_TIP
        mock_landmarks.landmark[14].x, mock_landmarks.landmark[14].y = 0.5, 0.4  # RING_FINGER_PIP
        mock_landmarks.landmark[20].x, mock_landmarks.landmark[20].y = 0.5, 0.5  # PINKY_TIP
        mock_landmarks.landmark[18].x, mock_landmarks.landmark[18].y = 0.5, 0.4  # PINKY_PIP

        # Create a mock image
        mock_image = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch('gestureControl.gesture_control.cv2.putText'):
            result = is_number_one(mock_landmarks, mock_image)
            self.assertTrue(result)

    def test_number_two_gesture(self):
        # Create a mock hand_landmarks object
        mock_landmarks = MagicMock()
        mock_landmarks.landmark = [MagicMock() for _ in range(21)]
        # Index and middle fingers extended, others folded
        mock_landmarks.landmark[8].x, mock_landmarks.landmark[8].y = 0.5, 0.2  # INDEX_FINGER_TIP
        mock_landmarks.landmark[6].x, mock_landmarks.landmark[6].y = 0.5, 0.4  # INDEX_FINGER_PIP
        mock_landmarks.landmark[12].x, mock_landmarks.landmark[12].y = 0.5, 0.2  # MIDDLE_FINGER_TIP
        mock_landmarks.landmark[10].x, mock_landmarks.landmark[10].y = 0.5, 0.4  # MIDDLE_FINGER_PIP
        mock_landmarks.landmark[16].x, mock_landmarks.landmark[16].y = 0.5, 0.5  # RING_FINGER_TIP
        mock_landmarks.landmark[14].x, mock_landmarks.landmark[14].y = 0.5, 0.4  # RING_FINGER_PIP
        mock_landmarks.landmark[20].x, mock_landmarks.landmark[20].y = 0.5, 0.5  # PINKY_TIP
        mock_landmarks.landmark[18].x, mock_landmarks.landmark[18].y = 0.5, 0.4  # PINKY_PIP

        # Create a mock image
        mock_image = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch('gestureControl.gesture_control.cv2.putText'):
            result = is_number_two(mock_landmarks, mock_image)
            self.assertTrue(result)

    def test_rock_on_gesture(self):
        # Create a mock hand_landmarks object
        mock_landmarks = MagicMock()
        mock_landmarks.landmark = [MagicMock() for _ in range(21)]
        # Index and pinky fingers extended, middle and ring folded
        mock_landmarks.landmark[8].x, mock_landmarks.landmark[8].y = 0.5, 0.2  # INDEX_FINGER_TIP
        mock_landmarks.landmark[6].x, mock_landmarks.landmark[6].y = 0.5, 0.4  # INDEX_FINGER_PIP
        mock_landmarks.landmark[12].x, mock_landmarks.landmark[12].y = 0.5, 0.5  # MIDDLE_FINGER_TIP
        mock_landmarks.landmark[10].x, mock_landmarks.landmark[10].y = 0.5, 0.4  # MIDDLE_FINGER_PIP
        mock_landmarks.landmark[16].x, mock_landmarks.landmark[16].y = 0.5, 0.5  # RING_FINGER_TIP
        mock_landmarks.landmark[14].x, mock_landmarks.landmark[14].y = 0.5, 0.4  # RING_FINGER_PIP
        mock_landmarks.landmark[20].x, mock_landmarks.landmark[20].y = 0.5, 0.2  # PINKY_TIP
        mock_landmarks.landmark[18].x, mock_landmarks.landmark[18].y = 0.5, 0.4  # PINKY_PIP

        # Create a mock image
        mock_image = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch('gestureControl.gesture_control.cv2.putText'):
            result = is_rock_on(mock_landmarks, mock_image)
            self.assertTrue(result)

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

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestGestureMQTT)
    CustomTestRunner(verbosity=0).run(suite)