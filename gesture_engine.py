import cv2
import mediapipe as mp
import numpy as np
import math
import time
import threading
from mouse_controller import FastMouseController

class UltraSmoothAdaptiveFilter:
    """Advanced 2-Stage Speed-Adaptive Motion Filter for Silky Smooth Cursor Control.
    Uses dynamic velocity scaling and dual exponential smoothing to eliminate hand tremors.
    """
    def __init__(self, min_cutoff=0.03, speed_scale=0.02, deadzone=1.0):
        self.min_cutoff = min_cutoff
        self.speed_scale = speed_scale
        self.deadzone = deadzone
        self.prev_x = None
        self.prev_y = None
        self.prev_time = None
        self.smooth_x = None
        self.smooth_y = None

    def filter(self, x, y):
        now = time.time()
        if self.prev_x is None:
            self.prev_x, self.prev_y = x, y
            self.smooth_x, self.smooth_y = x, y
            self.prev_time = now
            return x, y

        dt = now - self.prev_time
        if dt <= 0:
            dt = 0.001
        self.prev_time = now

        dx = x - self.prev_x
        dy = y - self.prev_y
        dist = math.hypot(dx, dy)

        # Micro-tremor deadzone filter
        if dist < self.deadzone:
            dx = 0.0
            dy = 0.0
            x = self.prev_x
            y = self.prev_y
            dist = 0.0

        speed = dist / dt  # pixels per second

        # Dynamic smoothing factor alpha [min_cutoff .. 1.0]
        alpha = self.min_cutoff + (1.0 - self.min_cutoff) * (1.0 - math.exp(-speed * self.speed_scale))
        alpha = max(0.01, min(1.0, alpha))

        # First stage exponential smoothing
        stage1_x = self.prev_x + alpha * dx
        stage1_y = self.prev_y + alpha * dy

        # Second stage low-pass smoothing for silk-smooth cursor movements
        beta = 0.55
        self.smooth_x = self.smooth_x * (1 - beta) + stage1_x * beta
        self.smooth_y = self.smooth_y * (1 - beta) + stage1_y * beta

        self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
        return self.smooth_x, self.smooth_y

    def reset(self):
        self.prev_x = None
        self.prev_y = None
        self.prev_time = None
        self.smooth_x = None
        self.smooth_y = None


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
        self.filter = UltraSmoothAdaptiveFilter(min_cutoff=0.03, speed_scale=0.02, deadzone=1.0)
        
        # Settings
        self.enabled = True
        self.enable_cursor = True
        self.enable_click = True
        self.enable_drag = True
        self.enable_scroll = True
        self.enable_zoom = True
        self.roi_margin = 0.15  # 15% margin for active control box
        self.click_threshold = 35
        self.right_click_threshold = 35
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

    def draw_tech_roi_box(self, frame, rx1, ry1, rx2, ry2, hand_in_roi):
        """Draw high-precision sleek tech reticle corner borders for active ROI zone"""
        color = (0, 255, 180) if hand_in_roi else (255, 160, 0)
        corner_len = 24
        thickness = 2

        # Outer bounding box rectangle
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), color, 1, cv2.LINE_AA)

        # Corner Brackets
        cv2.line(frame, (rx1, ry1), (rx1 + corner_len, ry1), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (rx1, ry1), (rx1, ry1 + corner_len), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (rx2, ry1), (rx2 - corner_len, ry1), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (rx2, ry1), (rx2, ry1 + corner_len), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (rx1, ry2), (rx1 + corner_len, ry2), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (rx1, ry2), (rx1, ry2 - corner_len), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (rx2, ry2), (rx2 - corner_len, ry2), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (rx2, ry2), (rx2, ry2 - corner_len), color, thickness, cv2.LINE_AA)

        # High-resolution HUD Text
        status_txt = "ACTIVE ROI ZONE [LOCKED]" if hand_in_roi else "ACTIVE ROI ZONE"
        cv2.putText(frame, status_txt, (rx1 + 8, ry1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    def process_frame(self, frame):
        t_start = time.perf_counter()
        
        if self.mirror:
            frame = cv2.flip(frame, 1)

        h, w, c = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        rx1, ry1 = int(w * self.roi_margin), int(h * self.roi_margin)
        rx2, ry2 = int(w * (1 - self.roi_margin)), int(h * (1 - self.roi_margin))

        self.hand_detected = bool(result.multi_hand_landmarks)
        hand_in_roi = False

        if self.hand_detected and self.enabled:
            hand_lms = result.multi_hand_landmarks[0]
            
            # Custom styled skeleton overlay
            self.mp_draw.draw_landmarks(
                frame, hand_lms, self.mp_hands.HAND_CONNECTIONS,
                self.mp_draw.DrawingSpec(color=(0, 255, 200), thickness=2, circle_radius=3),
                self.mp_draw.DrawingSpec(color=(255, 100, 0), thickness=2)
            )

            lm_list = [(int(lm.x * w), int(lm.y * h)) for lm in hand_lms.landmark]

            # Landmarks
            x_wrist, y_wrist = lm_list[0]
            x_thumb, y_thumb = lm_list[4]
            x_idx, y_idx = lm_list[8]
            x_idx_mcp, y_idx_mcp = lm_list[5]
            x_mid, y_mid = lm_list[12]
            x_mid_mcp, y_mid_mcp = lm_list[9]
            x_ring, y_ring = lm_list[16]
            x_ring_mcp, y_ring_mcp = lm_list[13]
            x_pinky, y_pinky = lm_list[20]
            x_pinky_mcp, y_pinky_mcp = lm_list[17]

            # Hand scale (Wrist to Middle MCP base)
            hand_scale = math.hypot(x_mid_mcp - x_wrist, y_mid_mcp - y_wrist)
            hand_scale = max(30.0, hand_scale)

            # Check inside ROI
            hand_in_roi = (rx1 <= x_idx <= rx2 and ry1 <= y_idx <= ry2)

            # Finger extension states
            dist_idx_wrist = math.hypot(x_idx - x_wrist, y_idx - y_wrist)
            dist_mid_wrist = math.hypot(x_mid - x_wrist, y_mid - y_wrist)
            dist_ring_wrist = math.hypot(x_ring - x_wrist, y_ring - y_wrist)
            dist_pinky_wrist = math.hypot(x_pinky - x_wrist, y_pinky - y_wrist)

            dist_idx_base = math.hypot(x_idx_mcp - x_wrist, y_idx_mcp - y_wrist)
            dist_mid_base = math.hypot(x_mid_mcp - x_wrist, y_mid_mcp - y_wrist)
            dist_ring_base = math.hypot(x_ring_mcp - x_wrist, y_ring_mcp - y_wrist)
            dist_pinky_base = math.hypot(x_pinky_mcp - x_wrist, y_pinky_mcp - y_wrist)

            index_extended = (dist_idx_wrist > 1.2 * dist_idx_base)
            middle_extended = (dist_mid_wrist > 1.2 * dist_mid_base)
            ring_extended = (dist_ring_wrist > 1.2 * dist_ring_base)
            pinky_extended = (dist_pinky_wrist > 1.2 * dist_pinky_base)

            all_fingers_folded = (not index_extended) and (not middle_extended) and (not ring_extended) and (not pinky_extended)
            all_fingers_open = index_extended and middle_extended and ring_extended and pinky_extended

            # Palm span (Thumb to Pinky distance)
            dist_thumb_pinky = math.hypot(x_thumb - x_pinky, y_thumb - y_pinky)
            span_ratio = dist_thumb_pinky / hand_scale

            # Map Index coordinate from ROI box to Full Screen bounds with clamping
            norm_x = np.interp(x_idx, (rx1, rx2), (0, self.mouse.screen_w))
            norm_y = np.interp(y_idx, (ry1, ry2), (0, self.mouse.screen_h))
            norm_x = float(np.clip(norm_x, 0, self.mouse.screen_w))
            norm_y = float(np.clip(norm_y, 0, self.mouse.screen_h))

            # Apply ultra-smooth speed-adaptive filter for butter-smooth tracking
            screen_x, screen_y = self.filter.filter(norm_x, norm_y)

            # Move cursor
            if self.enable_cursor and not all_fingers_folded:
                self.mouse.move_to(screen_x, screen_y)
                self.active_gesture = "MOVING"

            # Normalized pinch ratios
            dist_left = math.hypot(x_idx - x_thumb, y_idx - y_thumb)
            dist_right = math.hypot(x_mid - x_thumb, y_mid - y_thumb)
            
            ratio_left = dist_left / hand_scale
            ratio_right = dist_right / hand_scale

            thresh_ratio = self.click_threshold / 120.0

            is_left_pinched = ratio_left < thresh_ratio
            is_right_pinched = ratio_right < thresh_ratio and middle_extended

            # Visual touch lines & points
            cv2.line(frame, (x_idx, y_idx), (x_thumb, y_thumb), (0, 255, 0) if is_left_pinched else (0, 100, 255), 2, cv2.LINE_AA)
            if middle_extended:
                cv2.line(frame, (x_mid, y_mid), (x_thumb, y_thumb), (255, 0, 0) if is_right_pinched else (100, 100, 100), 1, cv2.LINE_AA)
            cv2.circle(frame, (x_idx, y_idx), 7, (255, 0, 255), cv2.FILLED, cv2.LINE_AA)

            # --- GESTURE LOGIC ---
            # 1. WINDOW ZOOM IN / ZOOM OUT GESTURE
            # Open Palm Wide (All 4 fingers extended + wide span) -> Zoom In (Ctrl +)
            # Closed Fist (All 4 fingers folded into palm) -> Zoom Out (Ctrl -)
            if all_fingers_open and span_ratio > 1.30 and self.enable_zoom and not is_left_pinched:
                zoomed = self.mouse.zoom_in()
                if zoomed:
                    self.active_gesture = "ZOOM IN (Ctrl +)"
                    print(f"👉 [VITS GESTURE ACTION]: {self.active_gesture}")
                    cv2.putText(frame, "ZOOM IN (Ctrl +)", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
            elif all_fingers_folded and self.enable_zoom and not is_left_pinched:
                zoomed = self.mouse.zoom_out()
                if zoomed:
                    self.active_gesture = "ZOOM OUT (Ctrl -)"
                    print(f"👉 [VITS GESTURE ACTION]: {self.active_gesture}")
                    cv2.putText(frame, "ZOOM OUT (Ctrl -)", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2, cv2.LINE_AA)

            # 2. LEFT CLICK & DRAG (Index + Thumb pinch)
            elif is_left_pinched:
                if not self.is_pinched:
                    self.is_pinched = True
                    self.pinch_start_time = time.time()
                
                hold_duration = time.time() - self.pinch_start_time
                if hold_duration > 0.25 and self.enable_drag:
                    self.mouse.start_drag()
                    if self.active_gesture != "DRAGGING":
                        self.active_gesture = "DRAGGING"
                        print(f"👉 [VITS GESTURE ACTION]: {self.active_gesture}")
                    cv2.putText(frame, "DRAG & DROP", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
            else:
                if self.is_pinched:
                    hold_duration = time.time() - self.pinch_start_time
                    if hold_duration <= 0.25 and self.enable_click:
                        clicked = self.mouse.left_click()
                        if clicked:
                            self.active_gesture = "LEFT CLICK"
                            print(f"👉 [VITS GESTURE ACTION]: {self.active_gesture}")
                            cv2.putText(frame, "LEFT CLICK", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
                    elif self.mouse.is_dragging:
                        self.mouse.stop_drag()
                        self.active_gesture = "RELEASED"
                        print(f"👉 [VITS GESTURE ACTION]: {self.active_gesture}")
                    self.is_pinched = False

            # 3. RIGHT CLICK (Thumb + Extended Middle finger pinch)
            if is_right_pinched and not self.is_pinched and self.enable_click and not all_fingers_folded:
                clicked = self.mouse.right_click()
                if clicked:
                    self.active_gesture = "RIGHT CLICK"
                    print(f"👉 [VITS GESTURE ACTION]: {self.active_gesture}")
                    cv2.putText(frame, "RIGHT CLICK", (40, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2, cv2.LINE_AA)

            # 4. SCROLLING (Two fingers Index + Extended Middle side-by-side gesture)
            dist_idx_mid = math.hypot(x_idx - x_mid, y_idx - y_mid)
            ratio_idx_mid = dist_idx_mid / hand_scale

            if ratio_idx_mid < 0.35 and middle_extended and not is_left_pinched and not all_fingers_folded and self.enable_scroll:
                if self.prev_scroll_y is not None:
                    dy = y_idx - self.prev_scroll_y
                    if abs(dy) > 5:
                        scroll_amount = - (dy / 8.0) * self.scroll_sensitivity
                        self.mouse.scroll(scroll_amount)
                        scroll_dir = "SCROLL UP" if dy < 0 else "SCROLL DOWN"
                        if self.active_gesture != scroll_dir:
                            self.active_gesture = scroll_dir
                            print(f"👉 [VITS GESTURE ACTION]: {self.active_gesture}")
                        cv2.putText(frame, scroll_dir, (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
                self.prev_scroll_y = y_idx
            else:
                self.prev_scroll_y = None

        else:
            self.filter.reset()
            self.prev_scroll_y = None
            if self.mouse.is_dragging:
                self.mouse.stop_drag()
            self.active_gesture = "SEARCHING HAND..." if self.enabled else "DISABLED"

        # Render high-precision tech ROI zone
        self.draw_tech_roi_box(frame, rx1, ry1, rx2, ry2, hand_in_roi)

        t_end = time.perf_counter()
        self.latency_ms = (t_end - t_start) * 1000
        return frame
