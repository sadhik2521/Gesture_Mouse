import customtkinter as ctk
from PIL import Image
import cv2
import time
import threading
import ctypes
try:
    from gestures.mouse_controller import FastMouseController
    from gestures.gesture_engine import GestureEngine, CameraStream
except ImportError:
    from mouse_controller import FastMouseController
    from gesture_engine import GestureEngine, CameraStream

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ModernGestureGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Gesture Mouse v5.0 PRECISION")
        self.geometry("1180x740")
        self.minsize(980, 640)
        self.configure(fg_color="#080c15")

        # Boost Windows multimedia timer resolution to 1 ms so time.sleep()
        # in the background processing thread stays accurate even when the
        # window is minimized or the app is not in focus.
        try:
            self._winmm = ctypes.windll.winmm
            self._winmm.timeBeginPeriod(1)
            self._timer_boosted = True
        except Exception:
            self._timer_boosted = False

        # Core modules
        self.mouse  = FastMouseController()
        self.engine = GestureEngine(self.mouse)
        self.camera_stream = None
        self.is_running    = False

        # Thread-safe result buffer: processing thread writes, GUI thread reads.
        self._proc_lock    = threading.Lock()
        self._proc_results = {
            "frame":      None,
            "fps":        0.0,
            "latency_ms": 0.0,
            "gesture":    "IDLE",
            "confidence": 0.0,
        }

        # Build UI
        self._build_header()
        self._build_main_layout()

        # Start engine
        self.start_engine()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ── Header ─────────────────────────────────────────────────────────────

    def _build_header(self):
        hf = ctk.CTkFrame(self, fg_color="#0d1829", corner_radius=0, height=62)
        hf.pack(fill="x", side="top")

        ctk.CTkLabel(
            hf,
            text="⚡ AI GESTURE MOUSE",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color="#38bdf8",
        ).pack(side="left", padx=20, pady=14)

        ctk.CTkLabel(
            hf,
            text="v5.0 PRECISION",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1e293b", text_color="#34d399",
            corner_radius=6, padx=8, pady=2,
        ).pack(side="left", padx=4)

        self.power_btn = ctk.CTkButton(
            hf,
            text="● ENGINE ACTIVE",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#059669", hover_color="#047857",
            width=148, height=36,
            command=self.toggle_engine,
        )
        self.power_btn.pack(side="right", padx=20, pady=13)

        self.settings_btn = ctk.CTkButton(
            hf,
            text="⚙",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="transparent",
            hover_color="#1e293b",
            text_color="#94a3b8",
            width=38, height=36,
            corner_radius=8,
            command=self.toggle_settings_panel,
        )
        self.settings_btn.pack(side="right", padx=(0, 4), pady=13)

    # ── Main layout ────────────────────────────────────────────────────────

    def _build_main_layout(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=18, pady=16)

        # ── Left column: video + metrics ──────────────────────────────────
        self.left_panel = ctk.CTkFrame(main, fg_color="#0d1829", corner_radius=12)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        left = self.left_panel

        ctk.CTkLabel(
            left,
            text="📷 PRECISION VISION FEED  (HD Enhanced)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#64748b",
        ).pack(anchor="w", padx=14, pady=(13, 4))

        self.video_container = ctk.CTkFrame(left, fg_color="#060a13", corner_radius=8)
        self.video_container.pack(fill="both", expand=True, padx=14, pady=4)

        self.video_label = ctk.CTkLabel(
            self.video_container,
            text="Initializing HD Camera…",
            font=ctk.CTkFont(size=13),
            text_color="#475569",
        )
        self.video_label.pack(fill="both", expand=True, padx=2, pady=2)

        # Metrics row
        mf = ctk.CTkFrame(left, fg_color="#0b1220", corner_radius=8)
        mf.pack(fill="x", padx=14, pady=(4, 14))

        self.fps_card = ctk.CTkLabel(
            mf, text="⚡ FPS: --",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8", width=110,
        )
        self.fps_card.pack(side="left", padx=12, pady=8)

        self.latency_card = ctk.CTkLabel(
            mf, text="⏱ Latency: -- ms",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a7f3d0", width=148,
        )
        self.latency_card.pack(side="left", padx=10, pady=8)

        self.conf_card = ctk.CTkLabel(
            mf, text="🖐 Conf: --",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#fb923c", width=100,
        )
        self.conf_card.pack(side="left", padx=10, pady=8)

        self.status_card = ctk.CTkLabel(
            mf, text="STATUS: IDLE",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1e293b", text_color="#facc15",
            corner_radius=6, padx=12, pady=3,
        )
        self.status_card.pack(side="right", padx=14, pady=7)

        # ── Right column: settings (hidden by default) ───────────────────
        self.right_panel = ctk.CTkFrame(main, fg_color="#0d1829", corner_radius=12, width=390)
        self.right_panel.pack_propagate(False)
        self._settings_visible = False
        right = self.right_panel

        # Panel header with close button
        panel_header = ctk.CTkFrame(right, fg_color="transparent")
        panel_header.pack(fill="x", padx=20, pady=(15, 4))

        ctk.CTkLabel(
            panel_header,
            text="⚙ CONTROL PANEL",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f1f5f9",
        ).pack(side="left")

        ctk.CTkButton(
            panel_header,
            text="✕",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="transparent",
            hover_color="#1e293b",
            text_color="#64748b",
            width=28, height=28,
            corner_radius=6,
            command=self.toggle_settings_panel,
        ).pack(side="right")

        sb = ctk.CTkScrollableFrame(right, fg_color="transparent")
        sb.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # ── Feature toggles ───────────────────────────────────────────────
        self._section(sb, "FEATURE TOGGLES")

        self.sw_cursor = self._switch(sb, "Cursor Tracking", True)
        self.sw_click  = self._switch(sb, "Left / Right Clicks", True)
        self.sw_drag   = self._switch(sb, "Drag & Drop Hold", True)
        self.sw_scroll = self._switch(sb, "Gesture Scroll", True)
        self.sw_zoom   = self._switch(sb, "Zoom In / Out", True)
        self.sw_close  = self._switch(sb, "Pinky Close Window (Alt+F4)", False)
        self.sw_dwell  = self._switch(sb, "Dwell Click (Hover 3s = Click)", True)
        self.sw_mirror = self._switch(sb, "Mirror Camera", True)
        self.sw_clahe  = self._switch(sb, "HD Camera Enhancement (CLAHE)", False)

        self._divider(sb)

        # ── Precision tuning ──────────────────────────────────────────────
        self._section(sb, "PRECISION TUNING")

        ctk.CTkLabel(sb, text="Cursor Smoothness  (lower = snappier / real-mouse feel):",
                     font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_cutoff = ctk.CTkSlider(sb, from_=0.05, to=0.50, number_of_steps=45,
                                       command=self.update_settings, progress_color="#38bdf8")
        self.sl_cutoff.set(0.18)
        self.sl_cutoff.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(sb, text="Active ROI Zone Size  (smaller = less arm movement):",
                     font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_roi = ctk.CTkSlider(sb, from_=0.03, to=0.25, number_of_steps=22,
                                    command=self.update_settings, progress_color="#38bdf8")
        self.sl_roi.set(0.08)
        self.sl_roi.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(sb, text="Pinch Sensitivity  (lower = tighter pinch needed):",
                     font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_pinch = ctk.CTkSlider(sb, from_=15, to=55, number_of_steps=40,
                                      command=self.update_settings, progress_color="#38bdf8")
        self.sl_pinch.set(32)
        self.sl_pinch.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(sb, text="Drag Hold Tolerance  (higher = easier hold while moving):",
                     font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_drag_tolerance = ctk.CTkSlider(sb, from_=1.2, to=2.5, number_of_steps=26,
                                              command=self.update_settings, progress_color="#38bdf8")
        self.sl_drag_tolerance.set(1.75)
        self.sl_drag_tolerance.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(sb, text="Scroll Speed:",
                     font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_scroll = ctk.CTkSlider(sb, from_=0.5, to=5.0, number_of_steps=45,
                                       command=self.update_settings, progress_color="#38bdf8")
        self.sl_scroll.set(2.0)
        self.sl_scroll.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(sb, text="Click Debounce  (frames held before click fires — lower = snappier):",
                     font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_debounce = ctk.CTkSlider(sb, from_=3, to=12, number_of_steps=9,
                                         command=self.update_settings, progress_color="#38bdf8")
        self.sl_debounce.set(6)
        self.sl_debounce.pack(fill="x", pady=(2, 10))

        self._divider(sb)

        # ── Camera setup ──────────────────────────────────────────────────
        self._section(sb, "CAMERA SETUP & STATUS")

        # ── DroidCam IP Stream (recommended for phone) ────────────────────
        dc_frame = ctk.CTkFrame(sb, fg_color="#0c1a2e", corner_radius=8)
        dc_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(dc_frame, text="📱 DroidCam / Phone Camera (Recommended)",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#38bdf8").pack(anchor="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(dc_frame,
                     text="Enter the IP shown in the DroidCam app on your phone:",
                     font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w", padx=10)

        ip_row = ctk.CTkFrame(dc_frame, fg_color="transparent")
        ip_row.pack(fill="x", padx=10, pady=(4, 8))

        self.ip_entry = ctk.CTkEntry(
            ip_row, placeholder_text="e.g. 192.168.1.5",
            fg_color="#1e293b", border_color="#334155", width=140
        )
        self.ip_entry.pack(side="left", padx=(0, 6))

        self.port_entry = ctk.CTkEntry(
            ip_row, placeholder_text="4747", width=60,
            fg_color="#1e293b", border_color="#334155"
        )
        self.port_entry.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            ip_row, text="▶ Connect",
            command=self.connect_droidcam_ip,
            fg_color="#059669", hover_color="#047857",
            font=ctk.CTkFont(size=11, weight="bold"), width=80, height=30
        ).pack(side="left")

        self.ip_status_label = ctk.CTkLabel(
            dc_frame, text="",
            font=ctk.CTkFont(size=10), text_color="#64748b", wraplength=200
        )
        self.ip_status_label.pack(anchor="w", padx=10, pady=(0, 6))

        # ── Fallback: physical webcam index ───────────────────────────────
        ctk.CTkLabel(sb, text="Or select a physical webcam:",
                     font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")

        self.cam_source_var = ctk.StringVar(value="Camera 0 (Default)")
        self.cam_source_combo = ctk.CTkOptionMenu(
            sb, values=["Camera 0 (Default)", "Camera 1", "Camera 2", "Camera 3", "Camera 4"],
            variable=self.cam_source_var, command=self.change_camera_source,
            fg_color="#1e293b", button_color="#334155", button_hover_color="#475569"
        )
        self.cam_source_combo.pack(fill="x", pady=(2, 6))

        self.cam_res_label = ctk.CTkLabel(
            sb, text="Resolution: initializing…",
            font=ctk.CTkFont(size=11), text_color="#64748b",
        )
        self.cam_res_label.pack(anchor="w", pady=(2, 8))

        self._divider(sb)


        # ── Gesture guide ─────────────────────────────────────────────────
        guide = ctk.CTkFrame(sb, fg_color="#0b1220", corner_radius=8)
        guide.pack(fill="x", pady=5)

        ctk.CTkLabel(guide, text="💡 GESTURE QUICK GUIDE",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#38bdf8").pack(anchor="w", padx=10, pady=(8, 4))

        guide_text = (
            "☝️  1 Finger (Index PIP)        → Move Cursor\n"
            "🤏  Pinch & Hold (Idx+Thumb)   → Drag & Drop (Open to Drop)\n"
            "✌️   Peace Sign (Index+Middle)  → Left Click\n"
            "👆  L-Shape (Thumb+Index)      → Right Click\n"
            "👍  Thumb Only                  → Double Click\n"
            "🖐  Open Palm (5 Fingers)       → Scroll Up / Down\n"
            "🤘  Rock Sign (Index + Pinky)   → Zoom In / Out\n"
            "🤙  Pinky Only (Shaka Sign)     → Close Window (Alt+F4)\n"
            "\n💡 Cursor only moves when EXACTLY 1 finger is up!"
        )
        ctk.CTkLabel(guide, text=guide_text,
                     font=ctk.CTkFont(size=10), text_color="#cbd5e1",
                     justify="left").pack(anchor="w", padx=10, pady=(0, 10))

    # ── Widget helpers ─────────────────────────────────────────────────────

    def _section(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#334155").pack(anchor="w", pady=(6, 5))

    def _divider(self, parent):
        ctk.CTkFrame(parent, fg_color="#1e293b", height=2).pack(fill="x", pady=10)

    def _switch(self, parent, label, default=True):
        sw = ctk.CTkSwitch(parent, text=label,
                           command=self.update_settings,
                           progress_color="#0284c7")
        if default:
            sw.select()
        sw.pack(anchor="w", pady=4)
        return sw

    # ── Settings sync ──────────────────────────────────────────────────────

    def update_settings(self, *_):
        self.engine.enable_cursor  = bool(self.sw_cursor.get())
        self.engine.enable_click   = bool(self.sw_click.get())
        self.engine.enable_drag    = bool(self.sw_drag.get())
        self.engine.enable_scroll  = bool(self.sw_scroll.get())
        self.engine.enable_zoom    = bool(self.sw_zoom.get())
        self.engine.enable_close   = bool(self.sw_close.get())
        self.engine.enable_dwell   = bool(self.sw_dwell.get())
        self.engine.mirror         = bool(self.sw_mirror.get())
        self.engine.enhance_camera = bool(self.sw_clahe.get())

        self.engine.filter.min_cutoff        = self.sl_cutoff.get()
        self.engine.roi_margin               = self.sl_roi.get()
        self.engine.click_threshold          = int(self.sl_pinch.get())
        self.engine.drag_release_multiplier  = float(self.sl_drag_tolerance.get())
        self.engine.scroll_sensitivity       = self.sl_scroll.get()
        self.engine._click_debounce          = int(round(self.sl_debounce.get()))

    def toggle_settings_panel(self):
        if self._settings_visible:
            self.right_panel.pack_forget()
            self._settings_visible = False
            self.settings_btn.configure(text_color="#94a3b8")
        else:
            self.left_panel.pack_forget()
            self.right_panel.pack(side="right", fill="both", expand=False, padx=(10, 0))
            self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
            self._settings_visible = True
            self.settings_btn.configure(text_color="#38bdf8")

    def toggle_engine(self):
        self.engine.enabled = not self.engine.enabled
        if self.engine.enabled:
            self.power_btn.configure(text="● ENGINE ACTIVE",
                                     fg_color="#059669", hover_color="#047857")
        else:
            self.power_btn.configure(text="○ ENGINE PAUSED",
                                     fg_color="#dc2626", hover_color="#b91c1c")

    # ── Camera & update loop ────────────────────────────────────────

    def _run_processing_loop(self):
        """
        Dedicated background daemon thread — runs at a fixed 60 Hz completely
        independent of the Tkinter event loop.  This guarantees gesture detection
        and cursor movement remain low-latency even when the window is minimized
        or another application has focus.
        """
        TARGET_INTERVAL = 1.0 / 60.0   # 60 Hz target
        frame_count  = 0
        fps_timer    = time.perf_counter()
        rolling_fps  = 0.0

        while self.is_running:
            t0 = time.perf_counter()

            ret, frame = self.camera_stream.read()
            if ret and frame is not None:
                annotated = self.engine.process_frame(frame)

                frame_count += 1
                elapsed = t0 - fps_timer
                if elapsed >= 1.0:
                    rolling_fps = frame_count / elapsed
                    frame_count = 0
                    fps_timer   = t0

                # Publish results for the GUI thread to consume
                with self._proc_lock:
                    self._proc_results["frame"]      = annotated
                    self._proc_results["fps"]        = rolling_fps
                    self._proc_results["latency_ms"] = self.engine.latency_ms
                    self._proc_results["gesture"]    = self.engine.active_gesture
                    self._proc_results["confidence"] = self.engine.hand_confidence

            # Adaptive sleep: wait out the remainder of the 16.67 ms budget
            processing_time = time.perf_counter() - t0
            sleep_time = TARGET_INTERVAL - processing_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    def start_engine(self, src=0):
        # 640x480 — natural brightness, works on all webcams
        self.camera_stream = CameraStream(src=src, width=640, height=480, fps=60)
        self.is_running    = True
        self.frame_count   = 0
        self.calculated_fps = 0.0

        # Launch the dedicated gesture processing thread.
        # It runs at 60 Hz independently of the Tkinter event loop, ensuring
        # cursor tracking stays smooth even when the window is minimized.
        self._proc_thread = threading.Thread(
            target=self._run_processing_loop,
            name="GestureProcessorThread",
            daemon=True,
        )
        self._proc_thread.start()

        # Start the GUI rendering loop (only updates the display).
        self.update_feed()

    def change_camera_source(self, choice):
        """Restart the camera stream on a background thread — never blocks the UI."""
        try:
            src = int(choice.split(" ")[1])
        except Exception:
            src = 0

        # Immediately update UI to show we're switching (stays responsive)
        self.video_label.configure(image="", text="⏳  Connecting to camera…")
        self.cam_res_label.configure(text="Resolution: connecting…")
        self.cam_source_combo.configure(state="disabled")

        def _switch():
            print(f"[SYSTEM]: Switching camera source to {src}...")
            self.is_running = False

            # Stop old stream
            if self.camera_stream:
                try:
                    self.camera_stream.stop()
                except Exception:
                    pass

            # Wait for processor thread (with generous timeout)
            if hasattr(self, '_proc_thread') and self._proc_thread.is_alive():
                self._proc_thread.join(timeout=2.0)

            # Start new stream (back on the main thread via after())
            self.after(0, lambda: self._finish_camera_switch(src))

        threading.Thread(target=_switch, daemon=True, name="CamSwitchThread").start()

    def connect_droidcam_ip(self):
        """Connect to DroidCam via direct IP stream (bypasses virtual camera driver)."""
        ip   = self.ip_entry.get().strip()
        port = self.port_entry.get().strip() or "4747"

        if not ip:
            self.ip_status_label.configure(
                text="⚠️ Please enter your phone's IP address.",
                text_color="#f59e0b"
            )
            return

        url = f"http://{ip}:{port}/video"
        self.ip_status_label.configure(
            text=f"Connecting to {url}…", text_color="#94a3b8"
        )

        # Reuse the non-blocking camera switch path
        self.video_label.configure(image="", text=f"⏳  Connecting to {url}…")
        self.cam_res_label.configure(text="Resolution: connecting…")

        def _switch():
            self.is_running = False
            if self.camera_stream:
                try:
                    self.camera_stream.stop()
                except Exception:
                    pass
            if hasattr(self, '_proc_thread') and self._proc_thread.is_alive():
                self._proc_thread.join(timeout=2.0)
            self.after(0, lambda: self._finish_ip_connect(url))

        threading.Thread(target=_switch, daemon=True, name="IPConnectThread").start()

    def _finish_ip_connect(self, url):
        """Start the engine with an IP stream URL on the main thread."""
        self.start_engine(src=url)
        # Give it 2 s then check if frames are arriving
        self.after(2000, lambda: self._check_ip_stream(url))

    def _check_ip_stream(self, url):
        ret, _ = self.camera_stream.read()
        if ret:
            self.ip_status_label.configure(
                text="✅ Connected! Phone camera is live.",
                text_color="#22c55e"
            )
        else:
            self.ip_status_label.configure(
                text="❌ No video. Check IP/port and ensure DroidCam app is open on phone.",
                text_color="#ef4444"
            )

    def _finish_camera_switch(self, src):

        """Called on the main thread once the old stream has safely stopped."""
        self.cam_source_combo.configure(state="normal")
        self.start_engine(src=src)


    def update_feed(self):
        """
        GUI rendering loop — only reads results from the processing thread and
        updates the display.  Runs at ~60 FPS when visible, throttled to 5 FPS
        (200 ms) when the window is minimized to avoid wasting CPU.
        """
        if not self.is_running:
            return

        # Read the latest processed results (thread-safe snapshot)
        with self._proc_lock:
            annotated    = self._proc_results["frame"]
            fps_val      = self._proc_results["fps"]
            latency_val  = self._proc_results["latency_ms"]
            gesture_val  = self._proc_results["gesture"]
            conf_val     = self._proc_results["confidence"]

        # Detect whether the window is minimized
        try:
            is_minimized = (self.state() == "iconic")
        except Exception:
            is_minimized = False

        # Always update the metric labels (cheap text ops)
        self.fps_card.configure(text=f"⚡ FPS: {fps_val:.1f}")
        self.latency_card.configure(text=f"⏱ Latency: {latency_val:.1f} ms")
        conf_pct = conf_val * 100
        self.conf_card.configure(
            text=f"🖐 Conf: {conf_pct:.0f}%" if conf_pct > 0 else "🖐 Conf: --"
        )
        self.status_card.configure(text=f"STATUS: {gesture_val}")

        # Only render the video frame when the window is actually visible
        if not is_minimized and annotated is not None:
            aw = self.camera_stream.actual_width
            ah = self.camera_stream.actual_height
            self.cam_res_label.configure(text=f"Resolution: {aw}×{ah}  |  Target: 640×480 @ 60 FPS")

            # Convert & display — Use cv2.resize for high performance
            cw = max(320, self.video_container.winfo_width()  - 8)
            ch = max(240, self.video_container.winfo_height() - 8)

            # Faster resize using OpenCV
            resized = cv2.resize(annotated, (cw, ch), interpolation=cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)

            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(cw, ch))
            self.video_label.configure(image=ctk_img, text="")

        # Schedule next GUI update:
        #   • 200 ms when minimized (5 FPS) — saves CPU, gesture loop is unaffected
        #   •  16 ms when visible  (60 FPS) — smooth display
        next_delay = 200 if is_minimized else 16
        self.after(next_delay, self.update_feed)

    def on_closing(self):
        self.is_running = False
        if self.camera_stream:
            self.camera_stream.stop()
        # Restore Windows timer resolution
        if self._timer_boosted:
            try:
                self._winmm.timeEndPeriod(1)
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    app = ModernGestureGUI()
    app.mainloop()
