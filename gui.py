import customtkinter as ctk
from PIL import Image
import cv2
import time
import threading
from mouse_controller import FastMouseController
from gesture_engine import GestureEngine, CameraStream

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ModernGestureGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Gesture Mouse v4.0 PRECISION")
        self.geometry("1180x740")
        self.minsize(980, 640)
        self.configure(fg_color="#080c15")

        # Core modules
        self.mouse  = FastMouseController()
        self.engine = GestureEngine(self.mouse)
        self.camera_stream = None
        self.is_running    = False

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
            text="v3.0 PRECISION",
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

    # ── Main layout ────────────────────────────────────────────────────────

    def _build_main_layout(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=18, pady=16)

        # ── Left column: video + metrics ──────────────────────────────────
        left = ctk.CTkFrame(main, fg_color="#0d1829", corner_radius=12)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

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

        # ── Right column: settings ────────────────────────────────────────
        right = ctk.CTkFrame(main, fg_color="#0d1829", corner_radius=12, width=390)
        right.pack(side="right", fill="both", expand=False, padx=(10, 0))
        right.pack_propagate(False)

        ctk.CTkLabel(
            right,
            text="⚙️ CONTROL PANEL",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f1f5f9",
        ).pack(anchor="w", padx=20, pady=(15, 8))

        sb = ctk.CTkScrollableFrame(right, fg_color="transparent")
        sb.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # ── Feature toggles ───────────────────────────────────────────────
        self._section(sb, "FEATURE TOGGLES")

        self.sw_cursor = self._switch(sb, "Cursor Tracking", True)
        self.sw_click  = self._switch(sb, "Left / Right Clicks", True)
        self.sw_drag   = self._switch(sb, "Drag & Drop Hold", True)
        self.sw_scroll = self._switch(sb, "Gesture Scroll", True)
        self.sw_zoom   = self._switch(sb, "Palm Zoom In / Out", True)
        self.sw_close  = self._switch(sb, "Pinky Close Window (Alt+F4)", False)
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

        ctk.CTkLabel(sb, text="Pinch Click Sensitivity  (lower = tighter pinch needed):",
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

        self._divider(sb)

        # ── Camera info ───────────────────────────────────────────────────
        self._section(sb, "CAMERA STATUS")
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
            "☝ 1 Finger (Index)   → Move Cursor\n"
            "✌ 2 Fingers (V-Sign)  → Left Click\n"
            "🤟 3 Fingers Extended → Right Click\n"
            "👍 Thumbs Up Pose     → Double Click (Open App/Folder)\n"
            "🤏 Pinch & Hold       → Drag & Drop (Spread fingers to Drop)\n"
            "🤙 Pinky Extended     → Close Window (Alt+F4)\n"
            "🖐 Open Palm (5 Fing) → Scroll Up/Down\n"
            "🤘 Rock Sign (Index+Pinky)→ Zoom In (Move Up) / Zoom Out (Move Down)\n"
            "\n💡 ULTRA-EASY CONTROL: Show finger signs for\n"
            "   instant mouse actions!"
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
        self.engine.mirror         = bool(self.sw_mirror.get())
        self.engine.enhance_camera = bool(self.sw_clahe.get())

        self.engine.filter.min_cutoff        = self.sl_cutoff.get()
        self.engine.roi_margin               = self.sl_roi.get()
        self.engine.click_threshold          = int(self.sl_pinch.get())
        self.engine.right_click_threshold    = int(self.sl_pinch.get())
        self.engine.drag_release_multiplier  = float(self.sl_drag_tolerance.get())
        self.engine.scroll_sensitivity       = self.sl_scroll.get()

    def toggle_engine(self):
        self.engine.enabled = not self.engine.enabled
        if self.engine.enabled:
            self.power_btn.configure(text="● ENGINE ACTIVE",
                                     fg_color="#059669", hover_color="#047857")
        else:
            self.power_btn.configure(text="○ ENGINE PAUSED",
                                     fg_color="#dc2626", hover_color="#b91c1c")

    # ── Camera & update loop ───────────────────────────────────────────────

    def start_engine(self):
        # 640x480 — natural brightness, works on all webcams
        self.camera_stream = CameraStream(src=0, width=640, height=480, fps=60)
        self.is_running    = True
        self.prev_time     = time.time()
        self.frame_count   = 0
        self.calculated_fps = 0.0
        self.update_feed()

    def update_feed(self):
        if not self.is_running:
            return

        ret, frame = self.camera_stream.read()
        if ret and frame is not None:
            annotated = self.engine.process_frame(frame)

            # FPS
            self.frame_count += 1
            now = time.time()
            if now - self.prev_time >= 1.0:
                self.calculated_fps = self.frame_count / (now - self.prev_time)
                self.frame_count    = 0
                self.prev_time      = now

            # Metrics
            self.fps_card.configure(text=f"⚡ FPS: {self.calculated_fps:.1f}")
            self.latency_card.configure(text=f"⏱ Latency: {self.engine.latency_ms:.1f} ms")
            conf_pct = self.engine.hand_confidence * 100
            self.conf_card.configure(
                text=f"🖐 Conf: {conf_pct:.0f}%" if conf_pct > 0 else "🖐 Conf: --"
            )
            self.status_card.configure(text=f"STATUS: {self.engine.active_gesture}")

            # Camera resolution label (updated once per second)
            aw = self.camera_stream.actual_width
            ah = self.camera_stream.actual_height
            self.cam_res_label.configure(text=f"Resolution: {aw}×{ah}  |  Target: 1280×720")

            # Convert & display — LANCZOS for high-quality upscaling
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)

            cw = max(320, self.video_container.winfo_width()  - 8)
            ch = max(240, self.video_container.winfo_height() - 8)
            img = img.resize((cw, ch), Image.Resampling.LANCZOS)

            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(cw, ch))
            self.video_label.configure(image=ctk_img, text="")

        # ~60 FPS update loop
        self.after(16, self.update_feed)

    def on_closing(self):
        self.is_running = False
        if self.camera_stream:
            self.camera_stream.stop()
        self.destroy()


if __name__ == "__main__":
    app = ModernGestureGUI()
    app.mainloop()
