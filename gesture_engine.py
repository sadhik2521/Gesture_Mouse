import cv2
import mediapipe as mp
import numpy as np
import math
import time
import threading
from mouse_controller import FastMouseController

class AdaptiveFilter:
    """Speed-adaptive exponential filter (One Euro Filter concept).
    Eliminates latency during fast motion and suppresses jitter during subtle movements.
    """
    def __init__(self, min_cutoff=0.08, speed_scale=0.015):
        self.min_cutoff = min_cutoff
        self.speed_scale = speed_scale
        self.prev_x = None
        self.prev_y = None
        self.prev_time = None

    def filter(self, x, y):
        now = time.time()
        if self.prev_x is None:
            self.prev_x, self.prev_y = x, y
            self.prev_time = now
            return x, y

        dt = now - self.prev_time
        if dt <= 0:
            dt = 0.001
        self.prev_time = now

        dx = x - self.prev_x
        dy = y - self.prev_y
        speed = math.hypot(dx, dy) / dt  # pixels per second

        # Dynamic smoothing factor alpha [min_cutoff .. 1.0]
        alpha = self.min_cutoff + (1.0 - self.min_cutoff) * (1.0 - math.exp(-speed * self.speed_scale))
        alpha = max(0.01, min(1.0, alpha))

        curr_x = self.prev_x + alpha * dx
        curr_y = self.prev_y + alpha * dy

        self.prev_x, self.prev_y = curr_x, curr_y
        return curr_x, curr_y

    def reset(self):
        self.prev_x = None
        self.prev_y = None
        self.prev_time = None


class CameraStream:
    """Threaded webcam reader for non-blocking high-FPS capture"""
    def __init__(self, src=0, width=640, height=480, fps=60):
        self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(src)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        self.ret, self.frame = self.cap.read()
        self.running = True
        self.lock = threading.Lock()
        
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.ret = ret
                    self.frame = frame
            else:
                time.sleep(0.005)

    def read(self):
        with self.lock:
            return self.ret, self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.cap.release()


class GestureEngine:
    def __init__(self, mouse_controller: FastMouseController):
        self.mouse = mouse_controller
        self.filter = AdaptiveFilter(min_cutoff=0.1, speed_scale=0.02)
        
        # Settings
        self.enabled = True
        self.enable_cursor = True
        self.enable_click = True
        self.enable_drag = True
        self.enable_scroll = True
        self.roi_margin = 0.15  # 15% margin on each side for active control box
        self.click_threshold = 35  # pixels distance between index & thumb for pinch
        self.right_click_threshold = 35 # distance between middle & thumb
        self.scroll_sensitivity = 1.5
        self.mirror = True

        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.mp_draw = mp.solutions.drawing_utils

        # Performance monitoring metrics
        self.fps = 0
        self.latency_ms = 0
        self.active_gesture = "IDLE"
        self.hand_detected = False
        
        # State tracking
        self.pinch_start_time = 0
        self.is_pinched = False
        self.prev_scroll_y = None

    def process_frame(self, frame):
        t_start = time.perf_counter()
        
        if self.mirror:
            frame = cv2.flip(frame, 1)

        h, w, c = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        # Draw ROI Box (Active Screen Mapping Region)
        rx1, ry1 = int(w * self.roi_margin), int(h * self.roi_margin)
        rx2, ry2 = int(w * (1 - self.roi_margin)), int(h * (1 - self.roi_margin))
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (255, 180, 0), 2)
        cv2.putText(frame, "ACTIVE ROI ZONE", (rx1 + 5, ry1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 180, 0), 1)

        self.hand_detected = bool(result.multi_hand_landmarks)

        if self.hand_detected and self.enabled:
            hand_lms = result.multi_hand_landmarks[0]
            
            # Custom styled skeleton overlay
            self.mp_draw.draw_landmarks(
                frame, hand_lms, self.mp_hands.HAND_CONNECTIONS,
                self.mp_draw.DrawingSpec(color=(0, 255, 200), thickness=2, circle_radius=3),
                self.mp_draw.DrawingSpec(color=(255, 100, 0), thickness=2)
            )

            lm_list = [(int(lm.x * w), int(lm.y * h)) for lm in hand_lms.landmark]

            x_idx, y_idx = lm_list[8]    # Index finger tip
            x_thumb, y_thumb = lm_list[4]# Thumb tip
            x_mid, y_mid = lm_list[12]   # Middle finger tip

            # Hand scale (Wrist to Middle MCP joint distance) for resolution & depth invariant thresholds
            hand_scale = math.hypot(lm_list[9][0] - lm_list[0][0], lm_list[9][1] - lm_list[0][1])
            hand_scale = max(30.0, hand_scale)

            # Finger tips & joints
            x_idx, y_idx = lm_list[8]      # Index finger tip
            x_thumb, y_thumb = lm_list[4]  # Thumb tip
            x_mid, y_mid = lm_list[12]     # Middle finger tip
            x_mid_mcp, y_mid_mcp = lm_list[9] # Middle finger base
            x_wrist, y_wrist = lm_list[0]   # Wrist

            # Check if Middle Finger is extended (distance to wrist vs base to wrist)
            dist_mid_to_wrist = math.hypot(x_mid - x_wrist, y_mid - y_wrist)
            dist_base_to_wrist = math.hypot(x_mid_mcp - x_wrist, y_mid_mcp - y_wrist)
            middle_extended = (dist_mid_to_wrist > 1.25 * dist_base_to_wrist)

            # Map Index coordinate from ROI box to Full Screen bounds
            norm_x = np.interp(x_idx, (rx1, rx2), (0, self.mouse.screen_w))
            norm_y = np.interp(y_idx, (ry1, ry2), (0, self.mouse.screen_h))

            # Apply speed-adaptive filter
            screen_x, screen_y = self.filter.filter(norm_x, norm_y)

            # Move cursor
            if self.enable_cursor:
                self.mouse.move_to(screen_x, screen_y)
                self.active_gesture = "MOVING"

            # Normalized pinch ratios
            dist_left = math.hypot(x_idx - x_thumb, y_idx - y_thumb)
            dist_right = math.hypot(x_mid - x_thumb, y_mid - y_thumb)
            
            ratio_left = dist_left / hand_scale
            ratio_right = dist_right / hand_scale

            # Dynamic threshold ratio based on slider value (slider 20-60 mapped to ratio ~0.15-0.45)
            thresh_ratio = self.click_threshold / 120.0

            # Visual touch lines & points
            is_left_pinched = ratio_left < thresh_ratio
            is_right_pinched = ratio_right < thresh_ratio and middle_extended

            cv2.line(frame, (x_idx, y_idx), (x_thumb, y_thumb), (0, 255, 0) if is_left_pinched else (0, 100, 255), 2)
            if middle_extended:
                cv2.line(frame, (x_mid, y_mid), (x_thumb, y_thumb), (255, 0, 0) if is_right_pinched else (100, 100, 100), 1)
            cv2.circle(frame, (x_idx, y_idx), 7, (255, 0, 255), cv2.FILLED)

            # --- GESTURE LOGIC ---
            # 1. LEFT CLICK & DRAG (Index + Thumb pinch)
            if is_left_pinched:
                if not self.is_pinched:
                    self.is_pinched = True
                    self.pinch_start_time = time.time()
                
                # Check hold duration for drag & drop
                hold_duration = time.time() - self.pinch_start_time
                if hold_duration > 0.25 and self.enable_drag:
                    self.mouse.start_drag()
                    self.active_gesture = "DRAGGING"
                    cv2.putText(frame, "DRAG & DROP", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                if self.is_pinched:
                    hold_duration = time.time() - self.pinch_start_time
                    if hold_duration <= 0.25 and self.enable_click:
                        # Quick pinch -> Left Click
                        clicked = self.mouse.left_click()
                        if clicked:
                            self.active_gesture = "LEFT CLICK"
                            cv2.putText(frame, "LEFT CLICK", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    elif self.mouse.is_dragging:
                        self.mouse.stop_drag()
                        self.active_gesture = "RELEASED"
                    self.is_pinched = False

            # 2. RIGHT CLICK (Thumb + Extended Middle finger pinch)
            if is_right_pinched and not self.is_pinched and self.enable_click:
                clicked = self.mouse.right_click()
                if clicked:
                    self.active_gesture = "RIGHT CLICK"
                    cv2.putText(frame, "RIGHT CLICK", (40, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

            # 3. SCROLLING (Two fingers Index + Extended Middle side-by-side gesture)
            dist_idx_mid = math.hypot(x_idx - x_mid, y_idx - y_mid)
            ratio_idx_mid = dist_idx_mid / hand_scale

            if ratio_idx_mid < 0.35 and middle_extended and not is_left_pinched and self.enable_scroll:
                if self.prev_scroll_y is not None:
                    dy = y_idx - self.prev_scroll_y
                    if abs(dy) > 5:  # noise filter threshold
                        scroll_amount = - (dy / 8.0) * self.scroll_sensitivity
                        self.mouse.scroll(scroll_amount)
                        self.active_gesture = "SCROLLING"
                        cv2.putText(frame, f"SCROLL {'UP' if dy < 0 else 'DOWN'}", (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                self.prev_scroll_y = y_idx
            else:
                self.prev_scroll_y = None

        else:
            self.filter.reset()
            self.prev_scroll_y = None
            if self.mouse.is_dragging:
                self.mouse.stop_drag()
            self.active_gesture = "SEARCHING HAND..." if self.enabled else "DISABLED"

        t_end = time.perf_counter()
        self.latency_ms = (t_end - t_start) * 1000
        return frame
