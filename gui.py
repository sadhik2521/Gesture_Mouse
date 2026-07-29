import customtkinter as ctk
from PIL import Image, ImageTk
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

        self.title("NEXUS AI - Low Latency Virtual Mouse")
        self.geometry("1120x720")
        self.minsize(980, 640)
        self.configure(fg_color="#0b0f19")  # Modern dark background

        # Core modules
        self.mouse = FastMouseController()
        self.engine = GestureEngine(self.mouse)
        self.camera_stream = None
        self.is_running = False

        # Build UI layout
        self._build_header()
        self._build_main_layout()

        # Start camera & loop
        self.start_engine()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="#131b2e", corner_radius=0, height=60)
        header_frame.pack(fill="x", side="top", padx=0, pady=0)

        # Title & Badge
        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ NEXUS AI GESTURE MOUSE",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color="#38bdf8"
        )
        title_label.pack(side="left", padx=20, pady=12)

        ver_badge = ctk.CTkLabel(
            header_frame,
            text="v2.0 LOW-LATENCY",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1e293b",
            text_color="#34d399",
            corner_radius=6,
            padx=8, pady=2
        )
        ver_badge.pack(side="left", padx=5)

        # Power Toggle Button
        self.power_btn = ctk.CTkButton(
            header_frame,
            text="● ENGINE ACTIVE",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            width=140, height=36,
            command=self.toggle_engine
        )
        self.power_btn.pack(side="right", padx=20, pady=12)

    def _build_main_layout(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Left Column: Video Feed & Metrics
        left_col = ctk.CTkFrame(main_container, fg_color="#131b2e", corner_radius=12)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        video_header = ctk.CTkLabel(
            left_col, text="📷 REALTIME VISION FEED & HUD",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#94a3b8"
        )
        video_header.pack(anchor="w", padx=15, pady=(15, 5))

        # Video Label Container
        self.video_container = ctk.CTkFrame(left_col, fg_color="#090d16", corner_radius=8)
        self.video_container.pack(fill="both", expand=True, padx=15, pady=5)

        self.video_label = ctk.CTkLabel(self.video_container, text="Initializing Camera Stream...")
        self.video_label.pack(fill="both", expand=True, padx=2, pady=2)

        # Metrics Card Row below video
        metrics_frame = ctk.CTkFrame(left_col, fg_color="#0f172a", corner_radius=8)
        metrics_frame.pack(fill="x", padx=15, pady=(5, 15))

        # Metric 1: FPS
        self.fps_card = ctk.CTkLabel(
            metrics_frame, text="⚡ FPS: --",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8",
            width=120
        )
        self.fps_card.pack(side="left", padx=15, pady=10)

        # Metric 2: Latency
        self.latency_card = ctk.CTkLabel(
            metrics_frame, text="⏱️ Latency: -- ms",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#a7f3d0",
            width=140
        )
        self.latency_card.pack(side="left", padx=15, pady=10)

        # Metric 3: Active Gesture Status Tag
        self.status_card = ctk.CTkLabel(
            metrics_frame, text="STATUS: IDLE",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1e293b", text_color="#facc15",
            corner_radius=6, padx=12, pady=4
        )
        self.status_card.pack(side="right", padx=15, pady=8)

        # Right Column: Controls & Configuration Panel
        right_col = ctk.CTkFrame(main_container, fg_color="#131b2e", corner_radius=12, width=380)
        right_col.pack(side="right", fill="both", expand=False, padx=(10, 0))
        right_col.pack_propagate(False)

        panel_title = ctk.CTkLabel(
            right_col, text="⚙️ CONTROL PANEL & SETTINGS",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#f8fafc"
        )
        panel_title.pack(anchor="w", padx=20, pady=(15, 10))

        # Scrollable container for settings
        settings_box = ctk.CTkScrollableFrame(right_col, fg_color="transparent")
        settings_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # --- Section 1: Feature Toggles ---
        sec1_title = ctk.CTkLabel(settings_box, text="FEATURE TOGGLES", font=ctk.CTkFont(size=12, weight="bold"), text_color="#64748b")
        sec1_title.pack(anchor="w", pady=(5, 5))

        self.sw_cursor = ctk.CTkSwitch(settings_box, text="Cursor Tracking", command=self.update_settings, progress_color="#0284c7")
        self.sw_cursor.select()
        self.sw_cursor.pack(anchor="w", pady=6)

        self.sw_click = ctk.CTkSwitch(settings_box, text="Left / Right Clicks", command=self.update_settings, progress_color="#0284c7")
        self.sw_click.select()
        self.sw_click.pack(anchor="w", pady=6)

        self.sw_drag = ctk.CTkSwitch(settings_box, text="Drag & Drop Hold", command=self.update_settings, progress_color="#0284c7")
        self.sw_drag.select()
        self.sw_drag.pack(anchor="w", pady=6)

        self.sw_scroll = ctk.CTkSwitch(settings_box, text="Gesture Scroll", command=self.update_settings, progress_color="#0284c7")
        self.sw_scroll.select()
        self.sw_scroll.pack(anchor="w", pady=6)

        self.sw_mirror = ctk.CTkSwitch(settings_box, text="Mirror Camera Horizontal", command=self.update_settings, progress_color="#0284c7")
        self.sw_mirror.select()
        self.sw_mirror.pack(anchor="w", pady=6)

        # Divider
        ctk.CTkFrame(settings_box, fg_color="#1e293b", height=2).pack(fill="x", pady=15)

        # --- Section 2: Tuning Sliders ---
        sec2_title = ctk.CTkLabel(settings_box, text="SMOOTHNESS & SENSITIVITY", font=ctk.CTkFont(size=12, weight="bold"), text_color="#64748b")
        sec2_title.pack(anchor="w", pady=(0, 5))

        # Slider 1: Motion Filter Cutoff (Smoothness)
        ctk.CTkLabel(settings_box, text="Filter Smoothness (Low = Smooth, High = Fast):", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_cutoff = ctk.CTkSlider(settings_box, from_=0.02, to=0.3, number_of_steps=20, command=self.update_settings, progress_color="#38bdf8")
        self.sl_cutoff.set(0.10)
        self.sl_cutoff.pack(fill="x", pady=(2, 10))

        # Slider 2: ROI Margin
        ctk.CTkLabel(settings_box, text="Active ROI Box Size (Smaller = Less arm reach):", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_roi = ctk.CTkSlider(settings_box, from_=0.05, to=0.30, number_of_steps=25, command=self.update_settings, progress_color="#38bdf8")
        self.sl_roi.set(0.15)
        self.sl_roi.pack(fill="x", pady=(2, 10))

        # Slider 3: Pinch Click Distance
        ctk.CTkLabel(settings_box, text="Pinch Distance Threshold (Pixels):", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
        self.sl_pinch = ctk.CTkSlider(settings_box, from_=20, to=60, number_of_steps=40, command=self.update_settings, progress_color="#38bdf8")
        self.sl_pinch.set(35)
        self.sl_pinch.pack(fill="x", pady=(2, 10))

        # Divider
        ctk.CTkFrame(settings_box, fg_color="#1e293b", height=2).pack(fill="x", pady=15)

        # Quick Instructions Card
        guide_card = ctk.CTkFrame(settings_box, fg_color="#0f172a", corner_radius=8)
        guide_card.pack(fill="x", pady=5)

        ctk.CTkLabel(guide_card, text="💡 GESTURE QUICK GUIDE", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=10, pady=(8, 4))
        ctk.CTkLabel(guide_card, text="• Move Index finger to control cursor\n• Pinch Index + Thumb = Left Click\n• Hold Pinch > 0.25s = Drag & Drop\n• Pinch Middle + Thumb = Right Click\n• Join Index + Middle = Scroll Up/Down",
                     font=ctk.CTkFont(size=10), text_color="#cbd5e1", justify="left").pack(anchor="w", padx=10, pady=(0, 8))

    def update_settings(self, *args):
        self.engine.enable_cursor = bool(self.sw_cursor.get())
        self.engine.enable_click = bool(self.sw_click.get())
        self.engine.enable_drag = bool(self.sw_drag.get())
        self.engine.enable_scroll = bool(self.sw_scroll.get())
        self.engine.mirror = bool(self.sw_mirror.get())

        self.engine.filter.min_cutoff = self.sl_cutoff.get()
        self.engine.roi_margin = self.sl_roi.get()
        self.engine.click_threshold = int(self.sl_pinch.get())
        self.engine.right_click_threshold = int(self.sl_pinch.get())

    def toggle_engine(self):
        self.engine.enabled = not self.engine.enabled
        if self.engine.enabled:
            self.power_btn.configure(text="● ENGINE ACTIVE", fg_color="#059669", hover_color="#047857")
        else:
            self.power_btn.configure(text="○ ENGINE PAUSED", fg_color="#dc2626", hover_color="#b91c1c")

    def start_engine(self):
        self.camera_stream = CameraStream(src=0, width=640, height=480, fps=60)
        self.is_running = True
        self.prev_time = time.time()
        self.frame_count = 0
        self.calculated_fps = 0

        # Start update loop on main thread via tkinter after()
        self.update_feed()

    def update_feed(self):
        if not self.is_running:
            return

        ret, frame = self.camera_stream.read()
        if ret and frame is not None:
            # Process frame with gesture engine
            annotated_frame = self.engine.process_frame(frame)

            # FPS calculation
            self.frame_count += 1
            now = time.time()
            if now - self.prev_time >= 1.0:
                self.calculated_fps = self.frame_count / (now - self.prev_time)
                self.frame_count = 0
                self.prev_time = now

            # Update metrics UI
            self.fps_card.configure(text=f"⚡ FPS: {self.calculated_fps:.1f}")
            self.latency_card.configure(text=f"⏱️ Latency: {self.engine.latency_ms:.1f} ms")
            self.status_card.configure(text=f"STATUS: {self.engine.active_gesture}")

            # Convert BGR to RGB for Tkinter PIL display
            cv2_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2_image)

            # Resize dynamically to match container size
            cw = max(320, self.video_container.winfo_width() - 10)
            ch = max(240, self.video_container.winfo_height() - 10)
            img = img.resize((cw, ch), Image.Resampling.NEAREST)

            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(cw, ch))
            self.video_label.configure(image=ctk_img, text="")

        # Schedule next frame (~60 FPS target)
        self.after(16, self.update_feed)

    def on_closing(self):
        self.is_running = False
        if self.camera_stream:
            self.camera_stream.stop()
        self.destroy()

if __name__ == "__main__":
    app = ModernGestureGUI()
    app.mainloop()
