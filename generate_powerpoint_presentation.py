import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    # 16:9 widescreen slides
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    NAVY_BG = RGBColor(15, 23, 42)      # #0F172A Dark Navy
    CARD_BG = RGBColor(30, 41, 59)      # #1E293B Card Slate
    ACCENT_BLUE = RGBColor(56, 189, 248) # #38BDF8 Sky Blue
    ACCENT_WHITE = RGBColor(248, 250, 252)
    TEXT_MUTED = RGBColor(148, 163, 184) # Slate 400

    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    plots_dir = os.path.join(assets_dir, "plots")

    def add_blank_slide(title_text):
        blank_slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_slide_layout)

        # Background color
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = NAVY_BG
        bg.line.fill.background()

        # Top Header Bar
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(0.9))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.name = "Calibri"
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = ACCENT_BLUE

        return slide

    # ==========================================
    # SLIDE 1: Title Slide
    # ==========================================
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY_BG
    bg1.line.fill.background()

    tb1 = s1.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.333), Inches(3.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    
    p1_title = tf1.paragraphs[0]
    p1_title.text = "AI GESTURE MOUSE"
    p1_title.font.name = "Calibri"
    p1_title.font.size = Pt(44)
    p1_title.font.bold = True
    p1_title.font.color.rgb = ACCENT_BLUE

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "Touchless Desktop Human-Computer Interaction via MediaPipe & Win32 Kernel Driver"
    p1_sub.font.name = "Calibri"
    p1_sub.font.size = Pt(22)
    p1_sub.font.color.rgb = ACCENT_WHITE
    p1_sub.space_before = Pt(14)

    p1_tech = tf1.add_paragraph()
    p1_tech.text = "Python 3.8+ | OpenCV | MediaPipe 3D Mesh | Win32 SendInput | CustomTkinter | TensorFlow"
    p1_tech.font.name = "Calibri"
    p1_tech.font.size = Pt(14)
    p1_tech.font.color.rgb = TEXT_MUTED
    p1_tech.space_before = Pt(24)

    p1_auth = tf1.add_paragraph()
    p1_auth.text = "Presented by: Student Name / Department | Guided by: Faculty Guide"
    p1_auth.font.name = "Calibri"
    p1_auth.font.size = Pt(14)
    p1_auth.font.italic = True
    p1_auth.font.color.rgb = ACCENT_BLUE
    p1_auth.space_before = Pt(20)

    # Slide 2 to 15 definitions
    slides_data = [
        (
            2, "Base Paper / Literature Survey",
            [
                "Foundational Paper 1: Zhang et al. (Google Research, 2020) — 'MediaPipe Hands: On-device Real-time Hand Tracking'. Real-time 21 3D landmarks.",
                "Foundational Paper 2: Casiez et al. (CHI 2012) — '1€ Filter: Speed-based Low-pass Filter for Human Input'. Solves jitter vs. lag tradeoff.",
                "Prior HCI Approaches: Color-marker gloves & Haar Cascades suffered from illumination sensitivity and rigid calibration.",
                "Advancements: Modern single-stage detector + mesh regression enables 60+ FPS tracking using standard RGB webcams without depth sensors."
            ],
            None
        ),
        (
            3, "Abstract",
            [
                "Problem: Physical peripherals cause ergonomic strain (RSI) and risk pathogen transmission in sterile environments.",
                "Proposed Solution: Vision-driven virtual mouse tracking 21 3D hand keypoints with sub-millisecond kernel event dispatching.",
                "Precision Engineering: Dual-stage cascade filter (1€ + Kalman) reduces pointer jitter to <0.1 px.",
                "Key Quantitative Results: 99.7% ML gesture accuracy, 0.7 ms processing latency, and full 9-gesture desktop control suite."
            ],
            None
        ),
        (
            4, "Project Overview",
            [
                "Objective: High-performance, touchless mouse replacement operating on standard USB or mobile IP webcams.",
                "Multi-Threaded Architecture: Decouples 60 FPS vision processing from GUI rendering, eliminating background throttling.",
                "Comprehensive Interaction: Supports Cursor Move, Left/Right/Double Click, Drag & Drop, Scroll, Zoom, Alt+F4, and Smart Dwell.",
                "OS Native Integration: Uses Windows Win32 SendInput API with virtual desktop coordinate mapping."
            ],
            None
        ),
        (
            5, "Problem Statement & Motivation",
            [
                "Ergonomic Strain: Prolonged physical mouse usage leads to Carpal Tunnel Syndrome and repetitive strain injuries.",
                "Hygiene & Medical Safety: Surgeons and cleanroom operators require touch-free interaction to prevent contamination.",
                "Webcam Mouse Failures: Conventional virtual mice suffer from >15ms lag, high jitter (>18px), and 'click dipping'.",
                "OS Restrictions: High-level libraries (PyAutoGUI) fail on administrator (UAC) windows and lack background reliability."
            ],
            None
        ),
        (
            6, "Existing System vs Proposed System",
            [
                "Tracking Hardware: Existing uses color gloves / IR sensors | Proposed uses raw webcam 21 3D landmarks.",
                "Cursor Stability: Existing moving average suffers 10-18px jitter | Proposed 1€ + Kalman filter delivers <0.1px jitter.",
                "OS Integration: Existing uses user-space PyAutoGUI | Proposed uses kernel-level Win32 SendInput API.",
                "Click Dipping: Existing moves during finger curl | Proposed features Smart Target Lock (Instant Pose Freeze).",
                "Latency & FPS: Existing runs ~15-30 FPS with high lag | Proposed maintains dedicated 60 FPS with 0.7ms latency."
            ],
            None
        ),
        (
            7, "System Architecture / Block Diagram",
            [
                "Capture Layer: Webcam / DroidCam IP stream -> BGR to RGB -> CLAHE local contrast enhancement.",
                "Inference Layer: Google MediaPipe Hands extracts 21 3D spatial keypoints (63 dimensional coordinates).",
                "Processing Thread: 60 FPS daemon computes relative translation, scale invariance, and gesture pose classification.",
                "Filter & Kernel Layer: Dual-stage 1€ + Kalman cascade -> Win32 SendInput worker queue with anti-flooding.",
                "UI Thread: CustomTkinter dark dashboard renders video feedback, FPS telemetry, and sensitivity sliders."
            ],
            os.path.join(assets_dir, "ui_dashboard.jpg")
        ),
        (
            8, "Technologies Used",
            [
                "Programming Language: Python 3.8+ (High-performance C-extension bindings).",
                "Computer Vision: OpenCV (Video I/O, CLAHE) & Google MediaPipe Hands (21 3D Keypoint Mesh).",
                "Machine Learning: TensorFlow / Keras (Multi-Layer Perceptron trained on 1,800 landmark samples).",
                "Operating System API: Windows Win32 C-types SendInput, timeBeginPeriod(1) (1.0ms timer), UIAutomation.",
                "GUI Framework: CustomTkinter (Modern responsive dark theme UI) & NumPy (Vectorized transformations)."
            ],
            None
        ),
        (
            9, "Hand Gesture Recognition Suite",
            [
                "Move Cursor: 1 Finger Extended (Index Only) — strict single-finger rule prevents accidental motion.",
                "Left Click: Peace Sign (Index + Middle) — non-blocking SendInput click with 5-frame debounce.",
                "Right Click: L-Shape (Thumb + Index) — context menu trigger with instant coordinate lock.",
                "Double Click: Thumb Up Only — sequential left clicks with a 30ms hardware pause.",
                "Drag & Drop: Pinch & Hold (Thumb + Index) — 1.75x hysteresis release buffer; open hand to drop.",
                "Scroll & Zoom: Open Palm (Slide Up/Down to Scroll) | Rock Sign (Slide Up/Down to Zoom In/Out)."
            ],
            os.path.join(assets_dir, "gesture_signs_poster.jpg")
        ),
        (
            10, "System Workflow & Algorithm",
            [
                "Step 1 (Landmarks): Extract 21 3D landmarks (x_i, y_i, z_i) with wrist (Point 0) as reference origin.",
                "Step 2 (Translation Normalization): Δx_i = x_i - x_0, Δy_i = y_i - y_0, Δz_i = z_i - z_0 (63D vector).",
                "Step 3 (Scale Invariance): Normalizes coordinates using wrist-to-middle MCP Euclidean distance: S_hand.",
                "Step 4 (Pinch Detection): d_pinch = sqrt((x_8 - x_4)^2 + (y_8 - y_4)^2) compared against dynamic threshold.",
                "Step 5 (Extension Ratio): Tip-to-wrist vs MCP-to-wrist ratio (>1.05) discriminates extended from curled fingers.",
                "Step 6 (Event Dispatch): Validated gestures pass through anti-dip freeze and dispatch to Win32 worker."
            ],
            None
        ),
        (
            11, "Filtering & Coordinate Mapping",
            [
                "The Jitter Problem: Human tremor and sensor noise cause 10-20px cursor vibration.",
                "Stage 1 — 1€ Filter: Speed-adaptive cutoff frequency; high smoothing when slow, zero lag when moving quickly.",
                "Stage 2 — Kalman Filter: State estimation [x, y, dx, dy] minimizes Gaussian observation noise.",
                "Active Screen ROI: Maps camera sub-region [x1, y1, x2, y2] to full monitor [0, W] x [0, H], preventing arm strain.",
                "Anti-Dip Locking: Freezes cursor during finger bends, completely eliminating unintended drag on click."
            ],
            None
        ),
        (
            12, "GUI & System Implementation",
            [
                "CustomTkinter Dark Dashboard: Modern control center with real-time landmark visualizer overlay.",
                "Real-Time Telemetry: Live FPS monitor, active gesture state badges, and click debounce feedback.",
                "Configurable Parameters: Sliders for cursor sensitivity, smoothing strength, click thresholds, and ROI bounds.",
                "Camera Flexibility: Background camera hardware auto-scanner and direct DroidCam IP stream decoder.",
                "Power Efficiency: Throttles UI rendering to 5 FPS when minimized while maintaining 60 FPS mouse tracking."
            ],
            os.path.join(assets_dir, "ui_dashboard.jpg")
        ),
        (
            13, "Results & Performance Graphs",
            [
                "Model Accuracy: Reaches 99.7% training accuracy and 99.4% validation accuracy across 100 epochs.",
                "Categorical Loss: Exponential decay from 2.4 down to 0.038, demonstrating strong model confidence.",
                "Jitter Reduction: Pointer noise dropped from 18.5 px to <0.1 px via the hybrid filter cascade.",
                "Processing Latency: Optimized from 14.2 ms down to 0.7 ms, enabling fluid 60 FPS real-time control.",
                "Live Similarity: Real-time hand poses consistently match trained templates at >95% similarity."
            ],
            os.path.join(plots_dir, "paper_accuracy_loss_section.png")
        ),
        (
            14, "Advantages, Applications & Limitations",
            [
                "Advantages: Zero extra hardware cost, sub-millisecond latency, rock-solid stability, 9-gesture suite.",
                "Healthcare Applications: Sterile operating rooms, pathology labs, and touchless medical viewing.",
                "Accessibility Applications: Motor-impaired users unable to grip standard mice; RSI prevention.",
                "Public Terminals: Hygienic touch-free kiosks, ATM interfaces, and smart home control.",
                "Limitations: Sensitive to extreme low-light environments; potential shoulder fatigue during prolonged overhead use."
            ],
            None
        ),
        (
            15, "Conclusion & Future Scope",
            [
                "Conclusion: AI Gesture Mouse delivers a production-grade, zero-cost touchless HCI matching physical mouse fidelity.",
                "Key Highlights: 0.7ms latency, <0.1px jitter, 99.7% ML accuracy, dual-threaded architecture, and Win32 kernel execution.",
                "Future Scope 1 — Bimanual Interaction: Two-hand control (left hand for zooming/panning, right hand for pointer).",
                "Future Scope 2 — Cross-Platform Support: Linux (X11/Wayland) and macOS (Quartz Event Taps) drivers.",
                "Future Scope 3 — Multimodal Fusion: Combining webcam eye-gaze tracking for coarse targeting with hand gestures for clicking."
            ],
            None
        )
    ]

    for num, title, bullets, img_path in slides_data:
        slide = add_blank_slide(f"{num}. {title}")
        
        # Decide layout based on whether an image exists
        if img_path and os.path.exists(img_path):
            # Left side: text box (width = 6.2 inches)
            tb = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(6.2), Inches(5.3))
            tf = tb.text_frame
            tf.word_wrap = True
            for i, b in enumerate(bullets):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = f"• {b}"
                p.font.name = "Calibri"
                p.font.size = Pt(14)
                p.font.color.rgb = ACCENT_WHITE
                p.space_before = Pt(8)
                p.space_after = Pt(6)

            # Right side: Image
            try:
                slide.shapes.add_picture(img_path, Inches(7.4), Inches(1.5), width=Inches(5.1))
            except Exception as e:
                print(f"Warning: could not add image {img_path}: {e}")
        else:
            # Full width text box
            tb = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.3))
            tf = tb.text_frame
            tf.word_wrap = True
            for i, b in enumerate(bullets):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = f"• {b}"
                p.font.name = "Calibri"
                p.font.size = Pt(16)
                p.font.color.rgb = ACCENT_WHITE
                p.space_before = Pt(12)
                p.space_after = Pt(8)

    output_pptx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI_Gesture_Mouse_Presentation.pptx")
    prs.save(output_pptx)
    print(f"[+] Successfully generated PowerPoint presentation: {output_pptx}")

if __name__ == "__main__":
    create_presentation()
