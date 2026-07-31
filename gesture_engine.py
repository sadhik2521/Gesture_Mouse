# -*- coding: utf-8 -*-
import cv2
import mediapipe as mp
import numpy as np
import math
import time
import threading
from mouse_controller import FastMouseController


# ─────────────────────────────────────────────────────────────────────────────
# One Euro Filter  (best-in-class low-latency hand-tracking smoothing)
# Paper: "1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input"
# ─────────────────────────────────────────────────────────────────────────────
class _LowPassFilter:
    """Simple single-pole IIR low-pass filter (building block for One Euro)."""

    def __init__(self, alpha: float = 1.0):
        self._alpha = alpha
        self._y     = None
        self._s     = None

    def set_alpha(self, alpha: float):
        self._alpha = max(1e-6, min(1.0, alpha))

    def filter(self, value: float, alpha: float | None = None) -> float:
        if alpha is not None:
            self.set_alpha(alpha)
        if self._y is None:
            s = value
        else:
            s = self._alpha * value + (1.0 - self._alpha) * self._s
        self._y = value
        self._s = s
        return s

    @property
    def last_value(self) -> float:
        return self._s if self._s is not None else 0.0


class OneEuroFilter:
    """
    One Euro Filter — speed-adaptive low-pass filter for pointer/hand tracking.

    Key parameters:
        freq (float)       : nominal sample rate in Hz (e.g. 30)
        min_cutoff (float) : minimum cutoff frequency — lower = smoother when slow
        beta (float)       : speed coefficient — higher = more responsive when fast
        dcutoff (float)    : cutoff for derivative (usually 1.0, rarely changed)

    Tuning guide:
        • Reduce jitter when STILL  → decrease min_cutoff (e.g. 0.5 → 0.3)
        • Reduce lag when MOVING    → increase beta       (e.g. 0.1 → 0.4)
    """

    def __init__(self, freq: float = 30.0, min_cutoff: float = 0.5,
                 beta: float = 0.2, dcutoff: float = 1.0):
        self.freq       = max(1.0, freq)
        self.min_cutoff = min_cutoff
        self.beta       = beta
        self.dcutoff    = dcutoff
        self._x         = _LowPassFilter()
        self._dx        = _LowPassFilter()
        self._last_time = None

    # ── helper ────────────────────────────────────────────────────────────────
    @staticmethod
    def _alpha(cutoff: float, freq: float) -> float:
        """Compute IIR alpha from cutoff frequency and sample rate."""
        te  = 1.0 / freq
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / te)

    # ── main ──────────────────────────────────────────────────────────────────
    def filter(self, x: float, timestamp: float | None = None) -> float:
        if timestamp is None:
            timestamp = time.perf_counter()

        if self._last_time is None:
            freq = self.freq
        else:
            dt   = max(timestamp - self._last_time, 1e-6)
            freq = 1.0 / dt
        self._last_time = timestamp

        # Estimated speed (derivative of signal)
        prev_x  = self._x.last_value
        dx      = (x - prev_x) * freq
        edx     = self._dx.filter(dx, alpha=self._alpha(self.dcutoff, freq))

        # Adaptive cutoff: rises with speed so fast motion stays responsive
        cutoff  = self.min_cutoff + self.beta * abs(edx)
        return   self._x.filter(x, alpha=self._alpha(cutoff, freq))

    def reset(self):
        self._x         = _LowPassFilter()
        self._dx        = _LowPassFilter()
        self._last_time = None


# ─────────────────────────────────────────────────────────────────────────────
# 2-D One Euro Filter  (wraps two independent 1-D filters)
# ─────────────────────────────────────────────────────────────────────────────
class OneEuroFilter2D:
    """
    Applies independent One Euro filters to X and Y axes.

    Default tuning (min_cutoff=0.5, beta=0.25):
        • Near-zero jitter when hand is held still
        • No perceptible lag for fast swipes
        • Smooth diagonal arcs — no axis crosstalk
    """

    def __init__(self, freq: float = 30.0, min_cutoff: float = 0.5,
                 beta: float = 0.25, dcutoff: float = 1.0):
        self._fx = OneEuroFilter(freq, min_cutoff, beta, dcutoff)
        self._fy = OneEuroFilter(freq, min_cutoff, beta, dcutoff)

    def filter(self, x: float, y: float) -> tuple[float, float]:
        ts = time.perf_counter()
        return self._fx.filter(x, ts), self._fy.filter(y, ts)

    def reset(self):
        self._fx.reset()
        self._fy.reset()


# ─────────────────────────────────────────────────────────────────────────────
# Kalman Filter  (1-D constant-velocity model — predictive jitter removal)
# ─────────────────────────────────────────────────────────────────────────────
class KalmanFilter1D:
    """
    Simple 1-D constant-velocity Kalman filter for pointer smoothing.

    State vector: [position, velocity]
    Measurement:  [position]

    Parameters:
        process_noise (Q) : how much the model trusts prediction (lower = smoother)
        measurement_noise (R) : trust in raw measurement (higher = smoother but laggy)
        initial_estimate_error (P) : initial uncertainty
    """

    def __init__(self, process_noise: float = 1e-2,
                 measurement_noise: float = 0.5,
                 initial_estimate_error: float = 1.0):
        # State
        self._x  = np.zeros((2, 1), dtype=np.float64)   # [pos, vel]
        # Estimate covariance
        self._P  = np.eye(2, dtype=np.float64) * initial_estimate_error
        # Process noise covariance
        self._Q  = np.eye(2, dtype=np.float64) * process_noise
        self._Q[1, 1] *= 10.0   # higher uncertainty on velocity
        # Measurement noise covariance
        self._R  = np.array([[measurement_noise]], dtype=np.float64)
        # Measurement matrix: we only observe position
        self._H  = np.array([[1.0, 0.0]], dtype=np.float64)
        self._initialized = False

    def filter(self, z: float, dt: float = 1/30) -> float:
        dt = max(dt, 1e-6)
        # State transition matrix (constant velocity model)
        F = np.array([[1.0, dt], [0.0, 1.0]], dtype=np.float64)

        if not self._initialized:
            self._x[0, 0] = z
            self._initialized = True
            return z

        # Predict
        x_pred = F @ self._x
        P_pred = F @ self._P @ F.T + self._Q

        # Update (Kalman gain)
        S = self._H @ P_pred @ self._H.T + self._R
        K = P_pred @ self._H.T @ np.linalg.inv(S)

        # Measurement residual
        y = z - (self._H @ x_pred)[0, 0]

        self._x = x_pred + K * y
        self._P = (np.eye(2) - K @ self._H) @ P_pred
        return float(self._x[0, 0])

    def reset(self):
        self._x  = np.zeros((2, 1), dtype=np.float64)
        self._P  = np.eye(2, dtype=np.float64)
        self._initialized = False


# ─────────────────────────────────────────────────────────────────────────────
# Hybrid Precision Filter  (One Euro → Kalman cascade)
# ─────────────────────────────────────────────────────────────────────────────
class HybridPrecisionFilter:
    """
    Two-stage pipeline for maximum cursor stability with minimum lag:

      Stage 1: One Euro Filter
        - Eliminates high-frequency noise (tremor, camera quantization)
        - Speed-adaptive: smooth when slow, responsive when fast
        - No fixed delay — mathematically optimal for pointer tracking

      Stage 2: Kalman Filter (constant-velocity model)
        - Predictive smoothing for residual jitter
        - Slight trajectory prediction reduces subjective lag during fast swipes
        - Conservative tuning keeps prediction errors small

    Net result: cursor feels like a high-end gaming mouse even on a noisy
    webcam signal.
    """

    def __init__(self, freq: float = 30.0):
        # Stage 1 — One Euro (noise reduction, speed-adaptive)
        self._oef_x = OneEuroFilter(freq=freq, min_cutoff=0.4, beta=0.3,  dcutoff=1.0)
        self._oef_y = OneEuroFilter(freq=freq, min_cutoff=0.4, beta=0.3,  dcutoff=1.0)

        # Stage 2 — Kalman (residual jitter + micro-lag reduction)
        self._kf_x  = KalmanFilter1D(process_noise=5e-3, measurement_noise=0.3)
        self._kf_y  = KalmanFilter1D(process_noise=5e-3, measurement_noise=0.3)

        self._last_t = None

        # Deadzone: adaptive — shrinks when hand moves fast so cursor tracks exactly
        self.deadzone_px     = 1.2    # base dead-zone in screen-pixels
        self._last_fx        = None
        self._last_fy        = None

    def filter(self, x: float, y: float) -> tuple[float, float]:
        now = time.perf_counter()
        dt  = (now - self._last_t) if self._last_t is not None else 1/30
        dt  = max(dt, 1e-6)
        self._last_t = now

        # ── Stage 1: One Euro ──────────────────────────────────────────────
        ex = self._oef_x.filter(x, now)
        ey = self._oef_y.filter(y, now)

        # ── Stage 2: Kalman ────────────────────────────────────────────────
        kx = self._kf_x.filter(ex, dt)
        ky = self._kf_y.filter(ey, dt)

        # ── Adaptive dead-zone: suppress sub-pixel tremor ──────────────────
        if self._last_fx is not None:
            dist = math.hypot(kx - self._last_fx, ky - self._last_fy)
            speed = dist / dt
            # Dead-zone shrinks to ~0.3 px when speed > 300 px/s (fast swipe)
            dz = max(0.3, self.deadzone_px - speed * 0.003)
            if dist < dz:
                return self._last_fx, self._last_fy

        self._last_fx, self._last_fy = kx, ky
        return kx, ky

    def reset(self):
        self._oef_x.reset()
        self._oef_y.reset()
        self._kf_x.reset()
        self._kf_y.reset()
        self._last_t  = None
        self._last_fx = None
        self._last_fy = None


# ─────────────────────────────────────────────────────────────────────────────
# Threaded HD Camera Stream
# ─────────────────────────────────────────────────────────────────────────────
class CameraStream:
    """
    Threaded webcam reader: non-blocking frame capture at target resolution/FPS.
    Tries DirectShow (CAP_DSHOW) first for lowest latency on Windows.
    """

    def __init__(self, src=0, width=640, height=480, fps=60):
        self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(src)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        # Reset auto-exposure to automatic mode.
        # Diagnostic confirmed: 0.75 = auto (brightness ~160) on this camera.
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
        # Reset brightness to default (was stuck at 150 from a previous session)
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 128)

        # Read warmup frames so auto-exposure stabilizes before first real frame
        for _ in range(10):
            self.cap.read()
        self.ret, self.frame = self.cap.read()
        self.running = True
        self.lock    = threading.Lock()

        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.ret   = ret
                    self.frame = frame
            else:
                time.sleep(0.005)

    def read(self):
        with self.lock:
            return self.ret, (self.frame.copy() if self.frame is not None else None)

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.cap.release()

    @property
    def actual_width(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def actual_height(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


# ─────────────────────────────────────────────────────────────────────────────
# CLAHE + Gamma Enhancer — improves hand visibility in low/uneven light
# ─────────────────────────────────────────────────────────────────────────────
class CLAHEEnhancer:
    def __init__(self, clip_limit=2.5, tile_grid=(8, 8), gamma=1.4):
        self.clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
        # Precompute gamma LUT for fast per-pixel brightness boost
        self._build_gamma_lut(gamma)

    def _build_gamma_lut(self, gamma):
        """Build a 256-entry lookup table for gamma correction (brightness boost)."""
        inv_gamma = 1.0 / max(gamma, 0.1)
        self.gamma_lut = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in range(256)],
            dtype=np.uint8
        )

    def enhance(self, frame):
        """
        1. Apply gamma correction (software brightness boost — safe in any lighting)
        2. Apply CLAHE on luminance channel for local contrast improvement
        """
        # Step 1: gamma brightness lift
        bright = cv2.LUT(frame, self.gamma_lut)
        # Step 2: CLAHE on L channel of LAB
        lab = cv2.cvtColor(bright, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_eq = self.clahe.apply(l)
        lab_eq = cv2.merge((l_eq, a, b))
        return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)


# ─────────────────────────────────────────────────────────────────────────────
# Gesture Engine  (v4.0 — Hybrid Precision Filter Edition)
# ─────────────────────────────────────────────────────────────────────────────
class GestureEngine:
    def __init__(self, mouse_controller: FastMouseController):
        self.mouse  = mouse_controller

        # ── Hybrid precision filter (One Euro + Kalman cascade) ────────────
        self.filter = HybridPrecisionFilter(freq=30.0)
        self.clahe  = CLAHEEnhancer(clip_limit=2.5)

        # ── Feature toggles ────────────────────────────────────────────────
        self.enabled        = True
        self.enable_cursor  = True
        self.enable_click   = True
        self.enable_drag    = True
        self.enable_scroll  = True
        self.enable_zoom    = True
        self.enable_close   = True
        self.enhance_camera = False     # CLAHE — off by default (toggle in panel if needed)
        self.mirror         = True

        # ── Tuning parameters ──────────────────────────────────────────────
        # Smaller margin = larger usable hand zone = easier to reach edges/taskbar
        self.roi_margin         = 0.08   # 8% — gives full-screen reach comfortably
        self.click_threshold    = 32     # pinch distance (pixels) for left click
        self.right_click_threshold = 32
        self.scroll_sensitivity = 2.0
        # Edge overshoot: push mapping slightly past screen boundary so cursor
        # reaches 0 and screen_h (taskbar row) reliably
        self.edge_overshoot     = 0.02   # 2% extra mapping on each side

        # ── MediaPipe ──────────────────────────────────────────────────────
        self.mp_hands = mp.solutions.hands
        self.hands    = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,         # upgraded from 0 → 1 for better landmark accuracy
            min_detection_confidence=0.65,
            min_tracking_confidence=0.60,
        )
        self.mp_draw = mp.solutions.drawing_utils

        # ── Metrics ────────────────────────────────────────────────────────
        self.fps             = 0
        self.latency_ms      = 0
        self.active_gesture  = "IDLE"
        self.hand_detected   = False
        self.hand_confidence = 0.0

        # ── State tracking ─────────────────────────────────────────────────
        self.pinch_start_time  = 0.0
        self.is_pinched        = False
        self.prev_scroll_y     = None
        self.prev_zoom_y       = None

        # Double-click: deferred single-click approach
        # On first quick release we do NOT fire immediately — we wait up to
        # _double_click_gap seconds. If a second quick pinch-release arrives
        # in that window → double-click. Otherwise → single click.
        self._pending_click       = False   # True = a first click is waiting
        self._pending_click_time  = 0.0     # when the first release happened
        self._double_click_gap    = 0.40    # max gap between two pinches (seconds)

        # Cursor-still lock: when hand barely moves, lock cursor to prevent drift
        # Uses a circular buffer to detect true stillness (not just one-frame pause)
        self._still_frames     = 0
        self._still_threshold  = 6        # frames of stillness before locking (was 8)
        self._lock_x           = 0.0
        self._lock_y           = 0.0
        self._locked           = False
        self._still_buf        = []       # rolling window of last N positions
        self._still_buf_size   = 6        # size of the circular buffer

    # ── Drawing helpers ────────────────────────────────────────────────────

    def _draw_roi_box(self, frame, rx1, ry1, rx2, ry2, hand_in_roi):
        color      = (0, 255, 140) if hand_in_roi else (255, 160, 0)
        corner_len = 22
        t          = 2

        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), color, 1, cv2.LINE_AA)
        # Four corner L-brackets
        for cx, cy, sx, sy in [
            (rx1, ry1, +1, +1),
            (rx2, ry1, -1, +1),
            (rx1, ry2, +1, -1),
            (rx2, ry2, -1, -1),
        ]:
            cv2.line(frame, (cx, cy), (cx + sx * corner_len, cy), color, t, cv2.LINE_AA)
            cv2.line(frame, (cx, cy), (cx, cy + sy * corner_len), color, t, cv2.LINE_AA)

        label = "ROI LOCKED" if hand_in_roi else "ACTIVE ROI ZONE"
        cv2.putText(frame, label, (rx1 + 6, ry1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1, cv2.LINE_AA)

    def _draw_edge_indicator(self, frame, screen_x, screen_y, w, h):
        """Show a colored edge glow when cursor is near a screen boundary."""
        near = 60  # pixels from screen edge
        sw, sh = self.mouse.screen_w, self.mouse.screen_h
        indicators = []
        if screen_x < near:             indicators.append("◀ LEFT EDGE")
        if screen_x > sw - near:        indicators.append("RIGHT EDGE ▶")
        if screen_y < near:             indicators.append("▲ TOP EDGE")
        if screen_y > sh - near:        indicators.append("▼ TASKBAR ZONE")
        for i, txt in enumerate(indicators):
            cv2.putText(frame, txt, (w // 2 - 70, h - 30 - i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1, cv2.LINE_AA)

    # ── Main processing ────────────────────────────────────────────────────

    def process_frame(self, frame):
        t_start = time.perf_counter()

        if self.mirror:
            frame = cv2.flip(frame, 1)

        # CLAHE enhancement for clearer hand detection in any lighting
        if self.enhance_camera:
            frame = self.clahe.enhance(frame)

        h, w, _ = frame.shape
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result  = self.hands.process(rgb)

        # ROI bounds — Asymmetric Y-axis mapping for effortless Taskbar access
        # ry2 = h * (0.80 - margin) ensures moving hand down comfortably to ~70% camera height
        # maps 100% to screen height (the Taskbar row!) without needing to reach your desk.
        margin = self.roi_margin
        rx1 = int(w * margin)
        rx2 = int(w * (1.0 - margin))
        ry1 = int(h * margin)
        ry2 = int(h * (0.80 - margin))  # 70-72% height = Taskbar level!
        rx1 = max(0, rx1); ry1 = max(0, ry1)
        rx2 = min(w - 1, rx2); ry2 = max(ry1 + 20, min(h - 1, ry2))

        self.hand_detected   = bool(result.multi_hand_landmarks)
        self.hand_confidence = 0.0
        hand_in_roi          = False

        if self.hand_detected and self.enabled:
            hand_lms = result.multi_hand_landmarks[0]

            # Extract confidence if available
            if result.multi_handedness:
                self.hand_confidence = result.multi_handedness[0].classification[0].score

            # Draw skeleton overlay
            self.mp_draw.draw_landmarks(
                frame, hand_lms, self.mp_hands.HAND_CONNECTIONS,
                self.mp_draw.DrawingSpec(color=(0, 255, 200), thickness=2, circle_radius=3),
                self.mp_draw.DrawingSpec(color=(255, 120, 0), thickness=2),
            )

            lm = [(int(lm.x * w), int(lm.y * h)) for lm in hand_lms.landmark]

            # Key landmarks
            x_wrist,      y_wrist      = lm[0]
            x_thumb,      y_thumb      = lm[4]
            x_idx,        y_idx        = lm[8]   # Index tip
            x_idx_mcp,    y_idx_mcp    = lm[5]   # Index MCP (base)
            x_mid,        y_mid        = lm[12]  # Middle tip
            x_mid_mcp,    y_mid_mcp    = lm[9]
            x_ring,       y_ring       = lm[16]
            x_ring_mcp,   y_ring_mcp   = lm[13]
            x_pinky,      y_pinky      = lm[20]
            x_pinky_mcp,  y_pinky_mcp  = lm[17]

            # Hand scale (wrist → middle MCP)
            hand_scale = max(30.0, math.hypot(x_mid_mcp - x_wrist, y_mid_mcp - y_wrist))

            # ── Cursor control position ────────────────────────────────────
            # Use Index fingertip directly for precise aiming
            ctrl_x = x_idx
            ctrl_y = y_idx

            hand_in_roi = (rx1 <= ctrl_x <= rx2 and ry1 <= ctrl_y <= ry2)

            # Finger extension detection
            def extended(tip_xy, mcp_xy, wrist_xy, ratio=1.2):
                d_tip  = math.hypot(tip_xy[0] - wrist_xy[0], tip_xy[1] - wrist_xy[1])
                d_base = math.hypot(mcp_xy[0] - wrist_xy[0], mcp_xy[1] - wrist_xy[1])
                return d_tip > ratio * d_base

            wrist_xy    = (x_wrist, y_wrist)
            index_ext   = extended((x_idx,   y_idx),   (x_idx_mcp,   y_idx_mcp),   wrist_xy)
            middle_ext  = extended((x_mid,   y_mid),   (x_mid_mcp,   y_mid_mcp),   wrist_xy)
            ring_ext    = extended((x_ring,  y_ring),  (x_ring_mcp,  y_ring_mcp),  wrist_xy)
            pinky_ext   = extended((x_pinky, y_pinky), (x_pinky_mcp, y_pinky_mcp), wrist_xy)

            all_folded = not (index_ext or middle_ext or ring_ext or pinky_ext)
            all_open   = index_ext and middle_ext and ring_ext and pinky_ext

            # ── Screen mapping with edge overshoot ────────────────────────
            sw, sh = self.mouse.screen_w, self.mouse.screen_h
            norm_x = np.interp(ctrl_x, (rx1, rx2), (0, sw - 1))
            norm_y = np.interp(ctrl_y, (ry1, ry2), (0, sh - 1))
            norm_x = float(np.clip(norm_x, 0, sw - 1))
            norm_y = float(np.clip(norm_y, 0, sh - 1))

            # ── Hybrid precision filter (One Euro + Kalman) ────────────────
            screen_x, screen_y = self.filter.filter(norm_x, norm_y)

            # ── Cursor stillness lock ──────────────────────────────────────
            # Rolling-buffer approach: require N consecutive close positions
            # before locking (prevents premature lock during slow deliberate moves)
            self._still_buf.append((screen_x, screen_y))
            if len(self._still_buf) > self._still_buf_size:
                self._still_buf.pop(0)

            if len(self._still_buf) == self._still_buf_size:
                xs = [p[0] for p in self._still_buf]
                ys = [p[1] for p in self._still_buf]
                spread = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
                if spread < 2.5:
                    # Hand is genuinely stationary — lock to centroid for precision
                    self._locked = True
                    self._lock_x = sum(xs) / len(xs)
                    self._lock_y = sum(ys) / len(ys)
                else:
                    self._locked = False

            final_x = self._lock_x if self._locked else screen_x
            final_y = self._lock_y if self._locked else screen_y

            # ── Move cursor ───────────────────────────────────────────────
            if self.enable_cursor and not all_folded:
                self.mouse.move_to(final_x, final_y)
                self.active_gesture = "MOVING"

            # ── Pinch distances (normalized to hand scale) ─────────────────
            dist_L = math.hypot(x_idx - x_thumb, y_idx - y_thumb)  # Index ↔ Thumb
            dist_R = math.hypot(x_mid - x_thumb, y_mid - y_thumb)  # Middle ↔ Thumb

            thresh = self.click_threshold / 100.0 * hand_scale

            is_left_pinched  = dist_L < thresh
            is_right_pinched = dist_R < thresh and middle_ext and not index_ext

            # Visual touch lines
            cv2.line(frame, (x_idx, y_idx), (x_thumb, y_thumb),
                     (0, 255, 80) if is_left_pinched else (0, 100, 255), 2, cv2.LINE_AA)
            if middle_ext:
                cv2.line(frame, (x_mid, y_mid), (x_thumb, y_thumb),
                         (255, 60, 0) if is_right_pinched else (80, 80, 80), 1, cv2.LINE_AA)
            # Index fingertip marker
            cv2.circle(frame, (x_idx, y_idx), 8, (255, 0, 220), cv2.FILLED, cv2.LINE_AA)
            cv2.circle(frame, (x_idx, y_idx), 8, (255, 255, 255), 1, cv2.LINE_AA)

            # ═══ GESTURE LOGIC ════════════════════════════════════════════════════════════
            # 1. SCROLL:       🖐 Open Palm (5 Fingers Extended) -> Pure Scrolling (NO Clicks!)
            # 2. ZOOM IN/OUT:  🤘 Rock Sign (Index + Pinky UP) -> Move UP (Zoom In) / Move DOWN (Zoom Out)
            # 3. PINCH & HOLD: 🤏 Touch Index + Thumb > 0.25s -> DRAG & DROP (Open fingers to drop!)
            # 4. QUICK PINCH:  🤏 Touch Index + Thumb < 0.25s -> DOUBLE CLICK (Open App/Folder)
            # 5. RIGHT CLICK:  🤟 3 Fingers Only (Index + Middle + Ring UP, Pinky FOLDED)
            # 6. LEFT CLICK:   ✌️ 2 Fingers Only (Index + Middle UP, Ring FOLDED / V-Sign)
            # 7. CLOSE WINDOW: 🤙 Pinky Extended Only (Shaka Sign) -> Alt+F4

            four_fingers   = index_ext and middle_ext and ring_ext and pinky_ext
            is_scroll_pose = four_fingers
            is_zoom_pose   = index_ext and pinky_ext and not middle_ext and not ring_ext

            # --- GESTURE 1: SCROLL UP / DOWN (Open Palm 5 Fingers) ---
            if is_scroll_pose and not is_left_pinched and self.enable_scroll:
                self.prev_zoom_y = None
                if self.prev_scroll_y is not None:
                    dy = y_idx - self.prev_scroll_y
                    if abs(dy) > 4:
                        scroll_amt = -(dy / 6.0) * self.scroll_sensitivity
                        self.mouse.scroll(scroll_amt)
                        direction = "SCROLL UP" if dy < 0 else "SCROLL DOWN"
                        if self.active_gesture != direction:
                            self.active_gesture = direction
                            print(f"[GESTURE]: {self.active_gesture}")
                        cv2.putText(frame, direction, (40, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 240, 0), 2, cv2.LINE_AA)
                self.prev_scroll_y = y_idx

            # --- GESTURE 2: ZOOM IN / ZOOM OUT (Rock Sign 🤘 Move UP / DOWN) ---
            elif is_zoom_pose and not is_left_pinched and self.enable_zoom:
                self.prev_scroll_y = None
                if self.prev_zoom_y is not None:
                    dy = y_idx - self.prev_zoom_y
                    if abs(dy) > 8:
                        if dy < 0:
                            done = self.mouse.zoom_in()
                            if done:
                                self.active_gesture = "ZOOM IN"
                                print(f"[GESTURE]: {self.active_gesture}")
                        else:
                            done = self.mouse.zoom_out()
                            if done:
                                self.active_gesture = "ZOOM OUT"
                                print(f"[GESTURE]: {self.active_gesture}")
                        cv2.putText(frame, f"ROCK {self.active_gesture}", (40, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2, cv2.LINE_AA)
                        self.prev_zoom_y = y_idx
                else:
                    self.prev_zoom_y = y_idx

            # --- GESTURE 3 & 4: PINCH (Pinch Hold = Drag, Quick Pinch = Double Click) ---
            elif is_left_pinched:
                self.prev_scroll_y = None
                self.prev_zoom_y   = None
                if not self.is_pinched:
                    self.is_pinched = True
                    self.pinch_start_time = time.perf_counter()

                hold_dur = time.perf_counter() - self.pinch_start_time
                if hold_dur > 0.25 and self.enable_drag:
                    # Pinch Hold > 0.25s -> DRAG START!
                    self.mouse.start_drag()
                    if self.active_gesture != "DRAGGING":
                        self.active_gesture = "DRAGGING"
                        print(f"[GESTURE]: {self.active_gesture}")
                    cv2.putText(frame, "DRAGGING (Pinch Hold)", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2, cv2.LINE_AA)
                else:
                    cv2.putText(frame, "PINCHING...", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2, cv2.LINE_AA)

            # --- GESTURE 5: RIGHT CLICK (3 Fingers Only: Index + Middle + Ring, Pinky FOLDED) ---
            elif index_ext and middle_ext and ring_ext and not pinky_ext and not is_left_pinched and self.enable_click:
                self.prev_scroll_y = None
                self.prev_zoom_y   = None
                done = self.mouse.right_click()
                if done:
                    self.active_gesture = "RIGHT CLICK"
                    print(f"[GESTURE]: {self.active_gesture}")
                    cv2.putText(frame, "RIGHT CLICK (3 Fingers)", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 60, 0), 2, cv2.LINE_AA)

            # --- GESTURE 6: LEFT CLICK (2 Fingers Only: Index + Middle, Ring FOLDED / V-Sign) ---
            elif index_ext and middle_ext and not ring_ext and not is_left_pinched and self.enable_click:
                self.prev_scroll_y = None
                self.prev_zoom_y   = None
                done = self.mouse.left_click()
                if done:
                    self.active_gesture = "LEFT CLICK"
                    print(f"[GESTURE]: {self.active_gesture}")
                    cv2.putText(frame, "LEFT CLICK (2 Fingers)", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 80), 2, cv2.LINE_AA)

            # --- GESTURE 7: CLOSE ACTIVE WINDOW (Pinky Finger Extended / Shaka) ---
            elif pinky_ext and not index_ext and not middle_ext and not ring_ext and self.enable_close:
                self.prev_scroll_y = None
                self.prev_zoom_y   = None
                done = self.mouse.close_window()
                if done:
                    self.active_gesture = "CLOSE WINDOW"
                    print(f"[GESTURE]: {self.active_gesture}")
                    cv2.putText(frame, "CLOSE WINDOW (Alt+F4)", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
            else:
                if not is_scroll_pose:
                    self.prev_scroll_y = None
                if not is_zoom_pose:
                    self.prev_zoom_y = None

                # Release pinch logic
                if self.is_pinched:
                    hold_dur = time.perf_counter() - self.pinch_start_time
                    if hold_dur <= 0.25 and self.enable_click:
                        # Quick pinch release < 0.25s -> DOUBLE CLICK!
                        done = self.mouse.double_click()
                        if done:
                            self.active_gesture = "DOUBLE CLICK"
                            print(f"[GESTURE]: {self.active_gesture}")
                            cv2.putText(frame, "DOUBLE CLICK", (40, 55),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2, cv2.LINE_AA)
                    elif self.mouse.is_dragging:
                        # Open fingers -> DROP!
                        self.mouse.stop_drag()
                        self.active_gesture = "DROP"
                        print(f"[GESTURE]: DROP")
                        cv2.putText(frame, "DROP", (40, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 80), 2, cv2.LINE_AA)

                    self.is_pinched = False

            # Edge indicators
            self._draw_edge_indicator(frame, final_x, final_y, w, h)

        else:
            # No hand detected — reset all state
            self.filter.reset()
            self.prev_scroll_y  = None
            self._still_frames  = 0
            self._still_buf     = []
            self._locked        = False
            if self.mouse.is_dragging:
                self.mouse.stop_drag()
            self.active_gesture  = "SEARCHING HAND..." if self.enabled else "DISABLED"
            self.hand_confidence = 0.0

        # ROI overlay
        self._draw_roi_box(frame, rx1, ry1, rx2, ry2, hand_in_roi)

        t_end           = time.perf_counter()
        self.latency_ms = (t_end - t_start) * 1000
        return frame
