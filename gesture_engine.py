# -*- coding: utf-8 -*-
import cv2
import mediapipe as mp
import numpy as np
import math
import os
import time
import threading
import uiautomation as auto
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

    def __init__(self, freq: float = 60.0):
        # Stage 1 — One Euro (noise reduction, speed-adaptive)
        # min_cutoff=0.5 is the classic sweet-spot for 60 Hz pointer tracking.
        # beta=0.07 keeps fast swipes responsive without over-smoothing.
        self._oef_x = OneEuroFilter(freq=freq, min_cutoff=0.5, beta=0.07, dcutoff=5.0)
        self._oef_y = OneEuroFilter(freq=freq, min_cutoff=0.5, beta=0.07, dcutoff=5.0)

        # Stage 2 — Kalman (residual jitter + micro-lag reduction)
        # Lower measurement_noise for tighter convergence; process_noise stays high for responsiveness.
        self._kf_x  = KalmanFilter1D(process_noise=1e-1, measurement_noise=0.03)
        self._kf_y  = KalmanFilter1D(process_noise=1e-1, measurement_noise=0.03)

        self._last_t = None

        # Deadzone: adaptive — 2.0 px when still, shrinks to ~0.3 px during fast swipe
        self.deadzone_px     = 2.0    # base dead-zone in screen-pixels
        self._last_fx        = None
        self._last_fy        = None

    @property
    def min_cutoff(self):
        return self._oef_x.min_cutoff

    @min_cutoff.setter
    def min_cutoff(self, value):
        self._oef_x.min_cutoff = value
        self._oef_y.min_cutoff = value

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
        # DroidCam (and most physical webcams) are DirectShow devices on Windows.
        # Try CAP_DSHOW first for ALL integer sources — it is the correct backend.
        # Fall back to MSMF then bare (auto) only if DSHOW fails.
        if isinstance(src, int):
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = cv2.VideoCapture(src, cv2.CAP_MSMF)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = cv2.VideoCapture(src)   # last resort: auto backend
        else:
            # IP URL or file path — use default backend
            self.cap = cv2.VideoCapture(src)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FPS, fps)
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 128)
            # Warmup frames so auto-exposure stabilises
            for _ in range(5):
                self.cap.read()

        self.ret, self.frame = self.cap.read()
        if not self.ret:
            print(f"[ERROR]: Camera {src} failed to capture frames.")
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
        self.filter = HybridPrecisionFilter(freq=60.0)  # match 60 Hz processing loop
        self.clahe  = CLAHEEnhancer(clip_limit=2.5)

        # ── Feature toggles ────────────────────────────────────────────────
        self.enabled        = True
        self.enable_cursor  = True
        self.enable_click   = True
        self.enable_drag    = True
        self.enable_scroll  = True
        self.enable_zoom    = True
        self.enable_close   = True
        self.enable_dwell   = True
        self.enable_ui_hover_click = True
        self.enhance_camera = False
        self.mirror         = True

        # ── Tuning parameters ──────────────────────────────────────────────
        self.roi_margin              = 0.08
        self.click_threshold       = 32     # pinch distance (px) relative to hand scale
        self.drag_release_multiplier = 1.75   # 1.75x distance hysteresis while dragging
        self.scroll_sensitivity      = 2.0
        self.edge_overshoot          = 0.02

        # ── MediaPipe ──────────────────────────────────────────────────────
        self.mp_hands = mp.solutions.hands
        self.hands    = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.75,  # higher = fewer false positives
            min_tracking_confidence=0.60,   # slightly lower = better lock-on once detected
        )
        self.mp_draw = mp.solutions.drawing_utils

        # ── Metrics ────────────────────────────────────────────────────────
        self.fps             = 0
        self.latency_ms      = 0
        self.active_gesture  = "IDLE"
        self.hand_detected   = False
        self.hand_confidence = 0.0

        # ── Drag & Drop state tracking ─────────────────────────────────────
        self.pinch_start_time     = 0.0
        self.is_pinched           = False
        self.drag_loss_frames     = 0
        self.max_drag_loss_frames = 10     # ~300ms dropout protection before dropping
        self.last_valid_drag_pos  = None

        # ── Scroll / Zoom state ────────────────────────────────────────────
        self.prev_scroll_y = None
        self.prev_zoom_y   = None

        # ── Cursor position history (freeze during click poses) ────────────
        self._locked      = False
        self._pos_history = []

        # ── Smart UI Hover Auto-Click ──────────────────────────────────────
        self._hover_element_id     = None
        self._hover_start_time     = 0.0
        self._hover_duration       = 3.0
        self._hover_fired          = False
        self._hover_check_interval = 0.25
        self._last_hover_check     = 0.0
        self._cached_ctrl_id       = None

        # ── Gesture debounce counters ──────────────────────────────────────
        self._lclick_frames  = 0   # consecutive frames index-bend held
        self._rclick_frames  = 0   # consecutive frames Peace-Sign held
        self._dclick_frames  = 0   # consecutive frames Thumb-only held
        self._close_frames   = 0   # consecutive frames Pinky-only held
        self._click_debounce = 3   # 3 frames (~50ms) for snappy, responsive triggers
        self._close_debounce = 12  # ~200 ms for safety close

        self.gesture_names = {
            0: "Move Cursor",
            1: "Drag & Drop",
            2: "Left Click",
            3: "Right Click",
            4: "Double Click",
            5: "Scroll",
            6: "Zoom",
            7: "Close Window",
            8: "Idle"
        }

        # ── Index-finger bend left-click (edge-triggered, fires ONCE per bend) ─
        # The gesture fires on the FALLING EDGE only: straight → bent transition.
        # _idx_was_straight tracks whether the finger was up last frame so we
        # don't re-fire while the finger stays curled down.
        self._idx_was_straight  = True   # True when index was extended last frame
        self._lclick_armed      = False  # True once bend is confirmed; reset on straighten
        self._lclick_cooldown_t = 0.0   # time of last fired click (extra guard)
        self._lclick_cooldown_s = 0.40  # 400 ms minimum between bend-clicks

        # ── EMA position history for anti-jitter cursor reference ──────────
        self._ema_x = None
        self._ema_y = None
        self._ema_alpha = 0.35   # lower = smoother history reference

        # ── Learned Dataset Gesture Templates ─────────────────────────────
        self.templates = {}
        self.load_dataset_templates()

    def load_dataset_templates(self, dataset_dir="dataset"):
        """Load mathematical gesture templates directly from the dataset."""
        x_path = os.path.join(dataset_dir, "X_gestures.npy")
        y_path = os.path.join(dataset_dir, "y_gestures.npy")
        if os.path.exists(x_path) and os.path.exists(y_path):
            try:
                X = np.load(x_path)
                y = np.load(y_path)
                templates = {}
                for i in range(9):
                    samples = X[y == i]
                    if len(samples) > 0:
                        templates[i] = np.mean(samples, axis=0)
                self.templates = templates
                print(f"[GestureEngine] Successfully loaded {len(self.templates)} learned gesture templates from {dataset_dir}/")
            except Exception as e:
                print(f"[GestureEngine] Warning loading dataset templates: {e}")

    # ── Drawing helpers ────────────────────────────────────────────────────

    def _draw_dwell_ring(self, frame, cx, cy, progress, w, h):
        """
        Draw a circular countdown ring around the index fingertip on the camera feed.
        progress: 0.0 → 1.0 (fraction of dwell time elapsed)
        cx, cy: position in camera-frame pixel coordinates
        """
        radius = 28
        thickness = 3
        # Background ring (dark grey)
        cv2.circle(frame, (cx, cy), radius, (60, 60, 60), thickness, cv2.LINE_AA)
        # Progress arc — sweeps clockwise from top
        angle = int(progress * 360)
        if angle > 0:
            # Green → Yellow → Orange as it fills up
            if progress < 0.5:
                color = (0, 255, 100)     # green
            elif progress < 0.8:
                color = (0, 230, 255)     # yellow
            else:
                color = (0, 140, 255)     # orange
            cv2.ellipse(frame, (cx, cy), (radius, radius),
                        -90, 0, angle, color, thickness + 1, cv2.LINE_AA)
        # Percentage text
        pct_text = f"{int(progress * 100)}%"
        cv2.putText(frame, pct_text, (cx - 14, cy + radius + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)

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
            self.drag_loss_frames = 0  # reset tracking loss counter when hand is visible
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
            x_thumb_cmc,  y_thumb_cmc  = lm[1]

            # Hand scale (wrist → middle MCP)
            hand_scale = max(30.0, math.hypot(x_mid_mcp - x_wrist, y_mid_mcp - y_wrist))

            # ── Pinch distances with Hysteresis (normalized to hand scale) ──
            dist_L = math.hypot(x_idx - x_thumb, y_idx - y_thumb)
            start_thresh = self.click_threshold / 100.0 * hand_scale

            if self.is_pinched or self.mouse.is_dragging:
                release_thresh = start_thresh * self.drag_release_multiplier
                is_left_pinched = dist_L < release_thresh
            else:
                is_left_pinched = dist_L < start_thresh

            # ── Cursor control position ────────────────────────────────────
            # During drag: use Index-Thumb midpoint to eliminate squeeze displacement.
            # During normal tracking: use Index PIP joint (lm[6]) — far more stable
            # than the raw fingertip (lm[8]) which is the jitteriest landmark.
            x_idx_pip, y_idx_pip = lm[6]   # Index PIP joint (proximal interphalangeal)
            if self.is_pinched or self.mouse.is_dragging:
                ctrl_x = int((x_idx + x_thumb) / 2)
                ctrl_y = int((y_idx + y_thumb) / 2)
            else:
                ctrl_x = x_idx_pip
                ctrl_y = y_idx_pip

            hand_in_roi = (rx1 <= ctrl_x <= rx2 and ry1 <= ctrl_y <= ry2)

            # ── Finger extension detection ─────────────────────────────────
            # Two-criterion check: (1) tip distance from wrist is > ratio*MCP distance,
            # AND (2) tip is above (lower Y value than) the MCP in image coords.
            # This handles bent-wrist poses that fool a single distance ratio check.
            # Reduced ratio to 1.15 to make middle finger much more forgiving to foreshortening!
            def extended(tip_xy, mcp_xy, wrist_xy, ratio=1.05):
                d_tip  = math.hypot(tip_xy[0] - wrist_xy[0], tip_xy[1] - wrist_xy[1])
                d_base = math.hypot(mcp_xy[0] - wrist_xy[0], mcp_xy[1] - wrist_xy[1])
                dist_ok = d_tip > ratio * d_base
                # Tip should be farther from wrist than its own MCP
                tip_far = d_tip > d_base * 1.05
                return dist_ok and tip_far

            wrist_xy    = (x_wrist, y_wrist)
            index_ext   = extended((x_idx,   y_idx),   (x_idx_mcp,   y_idx_mcp),   wrist_xy)
            middle_ext  = extended((x_mid,   y_mid),   (x_mid_mcp,   y_mid_mcp),   wrist_xy)
            ring_ext    = extended((x_ring,  y_ring),  (x_ring_mcp,  y_ring_mcp),  wrist_xy)
            pinky_ext   = extended((x_pinky, y_pinky), (x_pinky_mcp, y_pinky_mcp), wrist_xy)
            
            # Thumb extension: measure distance from thumb TIP to INDEX MCP (base of index finger).
            # When just pointing with index, thumb rests near the palm/index base → small distance.
            # When deliberately spread into L-shape, thumb moves far from index base → large distance.
            # This is much more reliable than CMC-to-tip which is always large due to thumb anatomy.
            thumb_to_idx_base = math.hypot(x_thumb - x_idx_mcp, y_thumb - y_idx_mcp)
            thumb_ext = thumb_to_idx_base > (hand_scale * 0.75)

            all_folded   = not (index_ext or middle_ext or ring_ext or pinky_ext)
            all_open     = index_ext and middle_ext and ring_ext and pinky_ext

            # ── Index-finger bend detection ────────────────────────────────
            # We use the robust `extended()` check which compares distance to the wrist.
            # When the finger curls, `index_ext` becomes False.
            index_is_bent = not index_ext

            # Gesture poses — computed BEFORE cursor movement so cursor can
            # be frozen immediately on click/close poses.

            # ── Stricter "clearly extended" check ──────────────────────────
            # ratio=1.45 (vs 1.05 for regular extended()) so that naturally-raised
            # but actually-folded fingers don't falsely block gesture poses.
            def clearly_extended(tip_xy, mcp_xy, wrist_xy, ratio=1.45):
                d_tip  = math.hypot(tip_xy[0] - wrist_xy[0], tip_xy[1] - wrist_xy[1])
                d_base = math.hypot(mcp_xy[0] - wrist_xy[0], mcp_xy[1] - wrist_xy[1])
                return d_tip > ratio * d_base and d_tip > d_base * 1.05

            index_clearly_ext  = clearly_extended((x_idx,   y_idx),   (x_idx_mcp,   y_idx_mcp),   wrist_xy)
            middle_clearly_ext = clearly_extended((x_mid,   y_mid),   (x_mid_mcp,   y_mid_mcp),   wrist_xy)
            ring_clearly_ext   = clearly_extended((x_ring,  y_ring),  (x_ring_mcp,  y_ring_mcp),  wrist_xy)
            pinky_clearly_ext  = clearly_extended((x_pinky, y_pinky), (x_pinky_mcp, y_pinky_mcp), wrist_xy)

            # ── Dynamic Gesture Template Matching (from Dataset) ──────────
            matched_gesture_id = None
            matched_sim = 0.0
            if self.templates:
                wrist_pt = hand_lms.landmark[0]
                live_features = []
                for pt in hand_lms.landmark:
                    live_features.extend([pt.x - wrist_pt.x, pt.y - wrist_pt.y, pt.z - wrist_pt.z])
                live_arr = np.array(live_features, dtype=np.float32)

                best_gid = None
                highest_sim = 0.0
                for gid, tmpl in self.templates.items():
                    dist = float(np.linalg.norm(tmpl - live_arr))
                    sim = math.exp(-dist * 4.5) * 100.0
                    if sim > highest_sim:
                        highest_sim = sim
                        best_gid = gid
                if highest_sim >= 35.0:
                    matched_gesture_id = best_gid
                    matched_sim = highest_sim

            if matched_gesture_id is not None:
                # ── Dynamic Template from Dataset has 100% PRIORITY ──
                is_strict_tracking = (matched_gesture_id == 0)
                is_left_pinched    = (matched_gesture_id == 1)
                is_lclick_pose     = (matched_gesture_id == 2)
                is_rclick_pose     = (matched_gesture_id == 3)
                is_dclick_pose     = (matched_gesture_id == 4)
                is_scroll_pose     = (matched_gesture_id == 5)
                is_zoom_pose       = (matched_gesture_id == 6)
                is_close_pose      = (matched_gesture_id == 7)
                all_folded         = (matched_gesture_id == 8)

                # Show live on-screen match badge matching live_test_graph.py
                g_text = f"AI: {self.gesture_names.get(matched_gesture_id, '')} ({int(matched_sim)}%)"
                cv2.putText(frame, g_text, (20, h - 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 120), 2, cv2.LINE_AA)
            else:
                # Geometric fallback when hand is outside dataset range
                is_close_pose  = pinky_ext and not index_clearly_ext and not middle_clearly_ext and not ring_clearly_ext
                is_lclick_pose = index_ext and middle_ext and not ring_clearly_ext and not pinky_clearly_ext
                is_rclick_pose = thumb_ext and index_ext and not middle_ext and not ring_clearly_ext and not pinky_clearly_ext
                is_dclick_pose = thumb_ext and not index_ext and not middle_ext and not all_open
                is_scroll_pose = index_ext and middle_ext and ring_ext and pinky_ext
                is_zoom_pose   = index_ext and pinky_ext and not middle_ext and not ring_ext
                is_strict_tracking = index_ext and not middle_ext and not ring_ext and not pinky_ext and not thumb_ext

            four_folded = all_folded

            # ── Screen mapping with edge overshoot ────────────────────────
            sw, sh = self.mouse.screen_w, self.mouse.screen_h
            norm_x = np.interp(ctrl_x, (rx1, rx2), (0, sw - 1))
            norm_y = np.interp(ctrl_y, (ry1, ry2), (0, sh - 1))
            norm_x = float(np.clip(norm_x, 0, sw - 1))
            norm_y = float(np.clip(norm_y, 0, sh - 1))

            # ── Hybrid precision filter (One Euro + Kalman) ────────────────
            screen_x, screen_y = self.filter.filter(norm_x, norm_y)

            # ── Cursor stillness lock ──────────────────────────────────────
            self._locked = False

            # Freeze cursor during click poses to prevent jitter/jumps, UNLESS dragging
            is_frozen = all_folded or is_close_pose or is_lclick_pose or is_rclick_pose or is_dclick_pose
            
            if is_frozen and self._pos_history:
                final_x, final_y = self._pos_history[-1]
            else:
                # EMA smoothing over recent filtered positions for anti-jitter reference.
                # This prevents single-frame snaps when transitioning between gestures.
                if self._ema_x is None:
                    self._ema_x, self._ema_y = screen_x, screen_y
                else:
                    self._ema_x = self._ema_alpha * screen_x + (1.0 - self._ema_alpha) * self._ema_x
                    self._ema_y = self._ema_alpha * screen_y + (1.0 - self._ema_alpha) * self._ema_y

                # ── Movement Threshold (Anti-Jitter Anchor) ───────────────
                # If movement is tiny (camera noise / hand tremor), lock the cursor completely.
                # It only breaks the lock if the smoothed position moves > 2.0 pixels away.
                if self._pos_history:
                    last_x, last_y = self._pos_history[-1]
                    dist = math.hypot(self._ema_x - last_x, self._ema_y - last_y)
                    if dist < 2.0:
                        final_x, final_y = last_x, last_y
                    else:
                        final_x, final_y = self._ema_x, self._ema_y
                else:
                    final_x = self._ema_x
                    final_y = self._ema_y
                    
                self._pos_history.append((final_x, final_y))
                if len(self._pos_history) > 10:
                    self._pos_history.pop(0)

            self.last_valid_drag_pos = (final_x, final_y)

            # ── Smart UI Hover Auto-Click ──────────────────────────────────────
            if getattr(self, 'enable_ui_hover_click', self.enable_dwell) and self.enable_cursor and not all_folded:
                now_hover = time.perf_counter()
                if now_hover - self._last_hover_check >= self._hover_check_interval:
                    self._last_hover_check = now_hover
                    try:
                        control = auto.ControlFromPoint(int(final_x), int(final_y))
                        rect = control.BoundingRectangle
                        self._cached_ctrl_id = (rect.left, rect.top, rect.right, rect.bottom, control.Name)
                    except Exception:
                        self._cached_ctrl_id = None

                ctrl_id = self._cached_ctrl_id
                if ctrl_id is not None:
                    now_hover = time.perf_counter()
                    if self._hover_element_id != ctrl_id:
                        self._hover_element_id = ctrl_id
                        self._hover_start_time = now_hover
                        self._hover_fired = False
                    else:
                        if not self._hover_fired:
                            elapsed = now_hover - self._hover_start_time
                            progress = min(1.0, elapsed / self._hover_duration)

                            self._draw_dwell_ring(frame, ctrl_x, ctrl_y, progress, w, h)

                            if progress >= 1.0:
                                try:
                                    control = auto.ControlFromPoint(int(final_x), int(final_y))
                                    name_label = control.Name if control.Name else "Element"
                                except Exception:
                                    name_label = "Element"
                                done = self.mouse.left_click()
                                if done:
                                    self.active_gesture = "AUTO UI CLICK"
                                    print(f"[GESTURE]: AUTO UI CLICK on '{name_label}' (held {self._hover_duration:.1f}s)")
                                    cv2.putText(frame, "UI AUTO CLICK!", (40, 55),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 80), 2, cv2.LINE_AA)
                                self._hover_fired = True
                            else:
                                cv2.putText(frame, f"HOVER {int(progress * 100)}%", (40, h - 50),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1, cv2.LINE_AA)
            else:
                self._hover_element_id = None
                self._hover_fired = False
                self._cached_ctrl_id = None

            # ── Move cursor ───────────────────────────────────────────────
            # The cursor ONLY MOVES if the user is in strict tracking mode 
            # (only index finger up). If they open another finger or pinch, it freezes.
            if self.enable_cursor and (is_strict_tracking or self.is_pinched):
                self.mouse.move_to(final_x, final_y)
                if self.active_gesture != "AUTO UI CLICK":
                    self.active_gesture = "MOVING"

            # ── Visual Pinch line & Fingertip marker ──────────────────────
            line_color = (0, 255, 255) if self.mouse.is_dragging else ((0, 255, 80) if is_left_pinched else (0, 100, 255))
            line_thick = 3 if self.mouse.is_dragging else 2
            cv2.line(frame, (x_idx, y_idx), (x_thumb, y_thumb), line_color, line_thick, cv2.LINE_AA)

            cv2.circle(frame, (x_idx, y_idx), 8, (255, 0, 220), cv2.FILLED, cv2.LINE_AA)
            cv2.circle(frame, (x_idx, y_idx), 8, (255, 255, 255), 1,         cv2.LINE_AA)

            if self.mouse.is_dragging:
                mid_x = int((x_idx + x_thumb) / 2)
                mid_y = int((y_idx + y_thumb) / 2)
                cv2.circle(frame, (mid_x, mid_y), 12, (0, 255, 255), 2, cv2.LINE_AA)

            # ═══ GESTURE LOGIC ═══════════════════════════════════════════════
            if matched_gesture_id is None:
                is_scroll_pose = index_ext and middle_ext and ring_ext and pinky_ext
                is_zoom_pose   = index_ext and pinky_ext and not middle_ext and not ring_ext
            # Note: is_rclick_pose (peace sign) already computed above before cursor freeze

            # --- GESTURE 1: SCROLL UP / DOWN (🖐 Open Palm) ---
            if is_scroll_pose and self.enable_scroll:
                self.prev_zoom_y = None
                self._lclick_frames = 0
                self._rclick_frames = 0
                self._close_frames  = 0
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

            # --- GESTURE 2: ZOOM IN / OUT (🤘 Rock Sign) ---
            elif is_zoom_pose and self.enable_zoom:
                self.prev_scroll_y  = None
                self._lclick_frames = 0
                self._rclick_frames = 0
                self._close_frames  = 0
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
                        cv2.putText(frame, f"ROCK 🤘 {self.active_gesture}", (40, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2, cv2.LINE_AA)
                        self.prev_zoom_y = y_idx
                else:
                    self.prev_zoom_y = y_idx

            # --- GESTURE 4: RIGHT CLICK (👉 L-Shape / Gun: Thumb + Index only) ---
            # NOTE: Checked BEFORE drag/pinch so the L-shape can't be eaten by the
            # pinch-distance check when thumb and index come close during the pose.
            elif is_rclick_pose and self.enable_click:
                self.prev_scroll_y  = None
                self.prev_zoom_y    = None
                self._lclick_frames = 0
                self._dclick_frames = 0
                self._close_frames  = 0
                self.is_pinched     = False  # prevent drag from arming while in r-click pose
                self._rclick_frames += 1
                if self._rclick_frames >= self._click_debounce:
                    done = self.mouse.right_click()
                    if done:
                        self.active_gesture = "RIGHT CLICK"
                        print(f"[GESTURE]: {self.active_gesture}")
                        cv2.putText(frame, "RIGHT CLICK (L-Shape)", (40, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 60, 0), 2, cv2.LINE_AA)
                else:
                    cv2.putText(frame, f"RIGHT CLICK... ({self._rclick_frames}/{self._click_debounce})", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 1, cv2.LINE_AA)

            # --- GESTURE 3: DRAG & DROP (🤏 Pinch & Hold Index + Thumb) ---
            # NOTE: Drag is checked AFTER click poses so explicit click gestures take priority.
            elif is_left_pinched:
                self.prev_scroll_y  = None
                self.prev_zoom_y    = None
                self._lclick_frames = 0
                self._rclick_frames = 0
                self._close_frames  = 0
                if not self.is_pinched:
                    self.is_pinched = True
                    self.pinch_start_time = time.perf_counter()

                hold_dur = time.perf_counter() - self.pinch_start_time
                if hold_dur > 0.30 and self.enable_drag:  # 0.30s hold prevents accidental drags
                    self.mouse.start_drag()
                    if self.active_gesture != "DRAGGING":
                        self.active_gesture = "DRAGGING"
                        print(f"[GESTURE]: {self.active_gesture}")
                    cv2.putText(frame, "DRAGGING 🤏 (Open fingers to Drop)", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2, cv2.LINE_AA)
                else:
                    cv2.putText(frame, "PINCHING...", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2, cv2.LINE_AA)

            # --- GESTURE 5: LEFT CLICK (Index + Middle / Peace Sign) ---
            elif is_lclick_pose and self.enable_click:
                self.prev_scroll_y  = None
                self.prev_zoom_y    = None
                self._rclick_frames = 0
                self._dclick_frames = 0
                self._close_frames  = 0

                self._lclick_frames += 1

                now_lc = time.perf_counter()
                if (self._lclick_frames >= self._click_debounce
                        and not self._lclick_armed
                        and (now_lc - self._lclick_cooldown_t) >= self._lclick_cooldown_s):
                    # We can click at slightly older stable coords to be ultra-safe
                    done = self.mouse.left_click()
                    if done:
                        self.active_gesture     = "LEFT CLICK"
                        self._lclick_armed      = True
                        self._lclick_cooldown_t = now_lc
                        print(f"[GESTURE]: {self.active_gesture}")
                        cv2.putText(frame, "LEFT CLICK (Peace Sign)", (40, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 80), 2, cv2.LINE_AA)
                elif self._lclick_armed:
                    cv2.putText(frame, "LEFT CLICK HELD (lower to reset)", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 200, 120), 1, cv2.LINE_AA)
                else:
                    cv2.putText(frame, f"LEFT CLICK... ({self._lclick_frames}/{self._click_debounce})", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 120), 1, cv2.LINE_AA)

            # --- GESTURE X: DOUBLE CLICK (Thumb Only) ---
            elif is_dclick_pose and self.enable_click:
                self.prev_scroll_y  = None
                self.prev_zoom_y    = None
                self._lclick_frames = 0
                self._rclick_frames = 0
                self._close_frames  = 0

                self._dclick_frames += 1
                if self._dclick_frames >= self._click_debounce:
                    try:
                        self.mouse.double_click()
                    except AttributeError:
                        self.mouse.left_click()
                        time.sleep(0.05)
                        self.mouse.left_click()
                    self.active_gesture = "DOUBLE CLICK"
                    print(f"[GESTURE]: {self.active_gesture}")
                    cv2.putText(frame, "DOUBLE CLICK 👍", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 200, 0), 2, cv2.LINE_AA)
                    # To prevent rapid re-fires, reset immediately
                    self._dclick_frames = -self._click_debounce * 2
                else:
                    cv2.putText(frame, f"DOUBLE CLICK... ({max(0, self._dclick_frames)}/{self._click_debounce})", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 100), 1, cv2.LINE_AA)

            # --- GESTURE 6: CLOSE WINDOW (🤙 Pinky Only / Shaka Sign) ---
            elif is_close_pose and self.enable_close:
                self.prev_scroll_y  = None
                self.prev_zoom_y    = None
                self._lclick_frames = 0
                self._rclick_frames = 0
                self._close_frames += 1
                if self._close_frames >= self._close_debounce:
                    done = self.mouse.close_window()
                    if done:
                        self.active_gesture = "CLOSE WINDOW"
                        print(f"[GESTURE]: {self.active_gesture}")
                        cv2.putText(frame, "CLOSE WINDOW 🤙 (Alt+F4)", (40, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 80, 255), 2, cv2.LINE_AA)
                else:
                    pct = int(self._close_frames / self._close_debounce * 100)
                    cv2.putText(frame, f"CLOSE WINDOW... {pct}%", (40, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 1, cv2.LINE_AA)

            else:
                # No gesture — reset all debounce counters
                self._lclick_frames = 0
                self._rclick_frames = 0
                self._close_frames  = 0
                if not is_scroll_pose:
                    self.prev_scroll_y = None
                if not is_zoom_pose:
                    self.prev_zoom_y = None

                # Release pinch logic (Drop)
                if self.is_pinched:
                    if self.mouse.is_dragging:
                        self.mouse.stop_drag()
                        self.active_gesture = "DROP"
                        print(f"[GESTURE]: DROP")
                        cv2.putText(frame, "DROP", (40, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 80), 2, cv2.LINE_AA)
                    self.is_pinched = False

            # Reset left-click arm when peace sign is lowered (outside elif chain)
            if not is_lclick_pose:
                self._lclick_frames = 0
                self._lclick_armed  = False

            # Edge indicators
            self._draw_edge_indicator(frame, final_x, final_y, w, h)

        else:
            # Check for hand-loss grace period while dragging
            if self.mouse.is_dragging and self.drag_loss_frames < self.max_drag_loss_frames:
                self.drag_loss_frames += 1
                if self.last_valid_drag_pos:
                    self.mouse.move_to(self.last_valid_drag_pos[0], self.last_valid_drag_pos[1])
                cv2.putText(frame, f"DRAGGING (Holding... {self.max_drag_loss_frames - self.drag_loss_frames}f)",
                            (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 200, 255), 2, cv2.LINE_AA)
                self.active_gesture = "DRAGGING (HOLDING)"
            else:
                self.drag_loss_frames = 0
                self.filter.reset()
                self._ema_x         = None  # reset EMA on hand loss
                self._ema_y         = None
                self.prev_scroll_y  = None
                self.prev_zoom_y    = None
                self._locked        = False
                self._lclick_frames = 0
                self._rclick_frames = 0
                self._close_frames  = 0
                if self.mouse.is_dragging:
                    self.mouse.stop_drag()
                    self.is_pinched = False
                    print("[GESTURE]: DROP (Hand Lost)")
                self.active_gesture  = "SEARCHING HAND..." if self.enabled else "DISABLED"
                self.hand_confidence = 0.0

        # ROI overlay
        self._draw_roi_box(frame, rx1, ry1, rx2, ry2, hand_in_roi)

        t_end           = time.perf_counter()
        self.latency_ms = (t_end - t_start) * 1000
        return frame
