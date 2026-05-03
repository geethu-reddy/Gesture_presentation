import time

import cv2
import pyautogui

from hand_tracker import HandTracker


pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

PREVIEW_WINDOW_NAME = "Camera Preview"


class GestureController:
    def __init__(self, status_callback=None, launch_mode="ppt_slideshow", show_preview=True):
        self.status_callback = status_callback or (lambda _message: None)
        self.launch_mode = launch_mode
        self.show_preview = show_preview

        self.is_running = False
        self._stop_requested = False
        self._control_started = False
        self._pointer_mode = "none"  # none | laser

        self._preview_size = (320, 190)
        self._screen_size = (1920, 1080)
        self._smoothed_cursor = None

    def run(self):
        tracker = HandTracker()
        camera = self._open_camera()

        if camera is None:
            self.status_callback("camera not opened")
            tracker.close()
            return

        self._screen_size = self._safe_screen_size()

        if self.show_preview:
            self._setup_preview_window()

        self.is_running = True
        self._stop_requested = False
        self._control_started = False
        self._pointer_mode = "none"
        self._smoothed_cursor = None
        self.status_callback("camera ready, show fist to start control")

        stable_gesture = "NONE"
        stable_frames = 0
        cooldown_seconds = 0.85
        last_action_time = 0.0

        try:
            while not self._stop_requested:
                ok, frame = camera.read()
                if not ok:
                    self.status_callback("camera frame not available")
                    break

                frame = cv2.flip(frame, 1)
                landmarks = tracker.get_landmarks(frame)
                gesture = tracker.get_gesture(landmarks)

                if gesture == stable_gesture:
                    stable_frames += 1
                else:
                    stable_gesture = gesture
                    stable_frames = 1

                now = time.time()
                is_stable = stable_frames >= 8
                cooldown_passed = now - last_action_time >= cooldown_seconds

                if is_stable and cooldown_passed:
                    if self._handle_gesture(stable_gesture):
                        last_action_time = now
                        stable_frames = 0

                if self._control_started and self._pointer_mode == "laser" and landmarks is not None:
                    self._update_laser_position(landmarks)

                if self.show_preview:
                    if not self._show_preview(frame, gesture):
                        self.status_callback("camera preview closed")
                        self.stop()
                        break
                else:
                    time.sleep(0.01)
        finally:
            camera.release()
            tracker.close()
            if self.show_preview:
                self._close_preview_window()
            self.is_running = False
            self._control_started = False
            self._pointer_mode = "none"
            self.status_callback("gesture control stopped")

    def _open_camera(self):
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        indices = [0, 1, 2]

        for idx in indices:
            for backend in backends:
                try:
                    cam = cv2.VideoCapture(idx, backend)
                except Exception:
                    cam = None

                if cam is None or not cam.isOpened():
                    if cam is not None:
                        cam.release()
                    continue

                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

                ok, _ = cam.read()
                if ok:
                    self.status_callback(f"camera opened (index {idx})")
                    return cam

                cam.release()

        return None

    def _handle_gesture(self, gesture):
        if gesture == "NONE":
            return False

        if gesture == "START_PRESENTATION":
            if self._control_started:
                self.status_callback("control already active")
                return True

            if self.launch_mode in {"ppt", "ppt_slideshow"}:
                pyautogui.click()   # 👈 bring PPT to focus
                time.sleep(0.3)
                pyautogui.press("f5")
            self._control_started = True
            self._pointer_mode = "none"
            self.status_callback("control started")
            return True

        if gesture == "END_PRESENTATION":
            if self.launch_mode in {"ppt", "ppt_slideshow"}:
                pyautogui.press("esc")
            self.status_callback("presentation ended")
            self.stop()
            return True

        if not self._control_started:
            self.status_callback("show fist first")
            return True

        if gesture == "NEXT_SLIDE":
            self._pointer_mode = "none"
            if self.launch_mode in {"ppt", "ppt_slideshow"}:
                pyautogui.press("right")
            else:
                pyautogui.press("right")
                pyautogui.press("pagedown")
            self.status_callback("next")
            return True

        if gesture == "PREV_SLIDE":
            self._pointer_mode = "none"
            if self.launch_mode in {"ppt", "ppt_slideshow"}:
                pyautogui.press("left")
            else:
                pyautogui.press("left")
                pyautogui.press("pageup")
            self.status_callback("previous")
            return True

        if gesture == "LASER_POINTER":
            self._pointer_mode = "laser"
            if self.launch_mode in {"ppt", "ppt_slideshow"}:
                pyautogui.hotkey("ctrl", "l")
            self.status_callback("laser mode")
            return True

        return False

    def _safe_screen_size(self):
        try:
            size = pyautogui.size()
            return int(size.width), int(size.height)
        except Exception:
            return 1920, 1080

    def _update_laser_position(self, landmarks):
        screen_w, screen_h = self._screen_size

        tip = landmarks[8]
        target_x = int(max(0, min(1, tip.x)) * screen_w)
        target_y = int(max(0, min(1, tip.y)) * screen_h)

        if self._smoothed_cursor is None:
            smoothed_x, smoothed_y = target_x, target_y
        else:
            prev_x, prev_y = self._smoothed_cursor
            smoothed_x = int(prev_x * 0.65 + target_x * 0.35)
            smoothed_y = int(prev_y * 0.65 + target_y * 0.35)

        self._smoothed_cursor = (smoothed_x, smoothed_y)

        try:
            pyautogui.moveTo(smoothed_x, smoothed_y, duration=0, _pause=False)
        except Exception:
            pass

    def _setup_preview_window(self):
        width, height = self._preview_size

        cv2.namedWindow(PREVIEW_WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(PREVIEW_WINDOW_NAME, width, height)

        screen_w, screen_h = self._screen_size
        x = max(0, screen_w - width - 16)
        y = max(0, screen_h - height - 70)
        cv2.moveWindow(PREVIEW_WINDOW_NAME, x, y)

        try:
            cv2.setWindowProperty(PREVIEW_WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
        except cv2.error:
            pass

    def _show_preview(self, frame, gesture):
        width, height = self._preview_size
        preview = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

        mode_text = "RUN" if self._control_started else "WAIT"
        pointer_text = self._pointer_mode.upper()
        cv2.rectangle(preview, (0, 0), (width, 56), (16, 16, 24), -1)
        cv2.putText(
            preview,
            f"Mode: {mode_text}  Pointer: {pointer_text}",
            (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (220, 220, 220),
            1,
        )
        cv2.putText(
            preview,
            f"Gesture: {gesture}",
            (10, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (220, 220, 220),
            1,
        )

        cv2.imshow(PREVIEW_WINDOW_NAME, preview)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            return False

        try:
            return cv2.getWindowProperty(PREVIEW_WINDOW_NAME, cv2.WND_PROP_VISIBLE) >= 1
        except cv2.error:
            return True

    def _close_preview_window(self):
        try:
            cv2.destroyWindow(PREVIEW_WINDOW_NAME)
        except cv2.error:
            pass

    def stop(self):
        self._stop_requested = True
