import cv2
import mediapipe as mp


class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self.handedness = "Right"

    def get_landmarks(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        if not results.multi_hand_landmarks:
            return None

        if results.multi_handedness:
            self.handedness = results.multi_handedness[0].classification[0].label

        return results.multi_hand_landmarks[0].landmark

    def fingers_up(self, landmarks):
        if self.handedness == "Right":
            thumb_up = landmarks[4].x < landmarks[3].x
        else:
            thumb_up = landmarks[4].x > landmarks[3].x

        index_up = landmarks[8].y < landmarks[6].y
        middle_up = landmarks[12].y < landmarks[10].y
        ring_up = landmarks[16].y < landmarks[14].y
        pinky_up = landmarks[20].y < landmarks[18].y

        return thumb_up, index_up, middle_up, ring_up, pinky_up

    def get_gesture(self, landmarks):
        if landmarks is None:
            return "NONE"

        thumb, index, middle, ring, pinky = self.fingers_up(landmarks)

        if thumb and index and middle and ring and pinky:
            return "END_PRESENTATION"

        if pinky and not thumb and not index and not middle and not ring:
            return "NEXT_SLIDE"

        if thumb and not index and not middle and not ring and not pinky:
            return "PREV_SLIDE"

        if index and not thumb and not middle and not ring and not pinky:
            return "LASER_POINTER"

        if not index and not middle and not ring and not pinky:
            return "START_PRESENTATION"

        return "NONE"

    def close(self):
        self.hands.close()
