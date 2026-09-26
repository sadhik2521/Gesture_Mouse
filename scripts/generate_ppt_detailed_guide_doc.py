import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_ppt_detailed_document():
    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    NAVY = RGBColor(15, 23, 42)
    BLUE = RGBColor(37, 99, 235)
    SLATE = RGBColor(71, 85, 105)
    DARK_TEXT = RGBColor(30, 41, 59)
    EMERALD = RGBColor(5, 150, 105)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = DARK_TEXT

    # Cover Page / Header
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("AI Gesture Mouse v5.0")
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(26)
    run_title.font.bold = True
    run_title.font.color.rgb = BLUE

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("15-Slide Presentation Companion & In-Depth Technical Guide")
    run_sub.font.name = 'Calibri'
    run_sub.font.size = Pt(15)
    run_sub.font.bold = True
    run_sub.font.color.rgb = NAVY

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_meta = p_meta.add_run("Slide-by-Slide Content, Technical Explanations, Presenter Scripts, and Viva Q&A")
    run_meta.font.size = Pt(10)
    run_meta.font.italic = True
    run_meta.font.color.rgb = SLATE

    doc.add_paragraph()

    def add_h1(text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(16)
        h.paragraph_format.space_after = Pt(6)
        run = h.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = BLUE
        return h

    def add_h2(text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        run = h.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = NAVY
        return h

    def add_bullet(bold_prefix, text):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(2)
        r1 = p.add_run(bold_prefix)
        r1.font.bold = True
        r1.font.color.rgb = NAVY
        p.add_run(text)
        return p

    slides_content = [
        {
            "num": 1,
            "title": "Title Slide",
            "slide_text": [
                ("Project Title: ", "AI Gesture Mouse — Touchless Desktop HCI System"),
                ("Subtitle: ", "Real-Time 3D Hand Tracking, Dual-Stage Precision Filtering & Kernel Event Emulation"),
                ("Technologies: ", "Python | MediaPipe Hands | OpenCV | Win32 SendInput | CustomTkinter"),
                ("Author / Presenter: ", "[Your Name / Roll Number / Department]"),
                ("Institutional Guide: ", "[Guide Name / University / College Name]")
            ],
            "explanation": "This slide sets the academic and technical tone of your defense or presentation. It identifies the project as an advanced Human-Computer Interaction (HCI) solution that leverages computer vision and machine learning to replace physical mice with a zero-hardware-cost webcam interface.",
            "speaker_notes": "\"Good morning respected evaluators and professors. Today, I am presenting 'AI Gesture Mouse: Multi-Threaded Touchless Desktop Control'. In this project, we eliminate the need for physical input devices by transforming any standard webcam or smartphone IP camera into a high-precision, sub-millisecond virtual mouse controller.\"",
            "viva_qa": [
                ("Q: Why is touchless HCI relevant today?", "A: It provides touchless, hygienic computing for medical and sterile environments, aids individuals with motor disabilities, prevents Repetitive Strain Injury (RSI), and paves the way for spatial computing interfaces without costly hardware sensors.")
            ]
        },
        {
            "num": 2,
            "title": "Base Paper & Literature Survey",
            "slide_text": [
                ("Foundational Paper 1: ", "Zhang et al. (Google Research, 2020) — 'MediaPipe Hands: On-device Real-time Hand Tracking'."),
                ("Foundational Paper 2: ", "Casiez et al. (CHI 2012) — '1€ Filter: A Simple Speed-based Low-pass Filter for Noisy and Laggy Human Input'."),
                ("Historical HCI Approaches: ", "Color-marker glove systems and optical flow methods suffered from rigid setups, high latency, and lighting instability."),
                ("Deep Learning Advancements: ", "Modern single-stage palm detection + landmark regression models achieve 3D tracking without specialized depth sensors (like Microsoft Kinect or Leap Motion).")
            ],
            "explanation": "Summarizes the academic evolution of vision-based mouse control. Early projects relied on color-based fingertip caps or Haar Cascades, which broke down in varying illumination. MediaPipe revolutionized on-device tracking by employing a two-stage pipeline: a BlazePalm detector followed by a 21-landmark 3D mesh regressor. Casiez's 1€ filter provides dynamic cutoff frequency scaling to balance jitter elimination at low speeds with zero-lag response during rapid flicks.",
            "speaker_notes": "\"Our literature review highlights two seminal breakthroughs: First, Google's MediaPipe Hands, which provides real-time 21 3D coordinates per hand in single-digit milliseconds. Second, Casiez's 1€ filter from CHI 2012, which solves the classic speed-accuracy tradeoff in human-computer interfaces. We bridge these academic contributions with kernel-level Windows event drivers.\"",
            "viva_qa": [
                ("Q: Why didn't you use specialized hardware like Leap Motion?", "A: Leap Motion requires proprietary infrared hardware ($100+). Our objective was universal accessibility using standard, ubiquitous RGB webcams costing under $10 or already built into laptops.")
            ]
        },
        {
            "num": 3,
            "title": "Abstract",
            "slide_text": [
                ("Problem Context: ", "Traditional physical peripherals cause ergonomic strain and are impractical in sterile or touch-free operating setups."),
                ("Core Innovation: ", "AI Gesture Mouse combines 21 3D hand landmarks, a 2-stage Hybrid Precision Filter (1€ + Kalman cascade), and a dedicated 60 FPS processing pipeline."),
                ("Benchmark Results: ", "99.7% gesture classification accuracy across 100 epochs, sub-0.7 ms processing latency, and <0.1 px pointer jitter."),
                ("System Capabilities: ", "Full desktop navigation: 9 intuitive hand gestures, Win32 kernel-level `SendInput` event dispatching, and DroidCam IP stream support.")
            ],
            "explanation": "The abstract is the condensed technical summary of the entire project. It outlines the core problem (hardware reliance, touch limitations, existing webcam mouse jitter), the solution engineered (dual-threaded Python engine with hybrid filtering), and quantitative benchmarks proving state-of-the-art stability.",
            "speaker_notes": "\"In this abstract, we summarize our work: While earlier virtual mice suffered from severe cursor shaking and high input lag, AI Gesture Mouse introduces a 2-stage hybrid precision filter and Windows kernel-level event dispatching. This reduces processing delay to 0.7 milliseconds and eliminates cursor jitter completely, achieving 99.7% gesture accuracy.\"",
            "viva_qa": [
                ("Q: What is the main differentiator of your project over existing open-source virtual mice?", "A: Most projects use basic PyAutoGUI with raw landmark coordinates, causing jitter (>15px) and cursor freezes during clicks. We implement dual-stage filtering, anti-dip cursor locking, and multithreaded Win32 kernel event execution.")
            ]
        },
        {
            "num": 4,
            "title": "Project Overview",
            "slide_text": [
                ("Primary Objective: ", "Develop a zero-latency, high-precision virtual mouse operable via standard webcams."),
                ("Core Design Philosophy: ", "Dual-Threaded Architecture decoupling 60 FPS vision processing from GUI rendering."),
                ("Comprehensive Gesture Suite: ", "9 distinct desktop controls: Move, Left Click, Right Click, Double Click, Drag & Drop, Scroll, Zoom, Window Close, and Smart Hover."),
                ("Operating System Integration: ", "Kernel-level execution compatible with Windows UAC prompts, Taskbar, and multi-monitor setups.")
            ],
            "explanation": "This slide outlines the broad project vision and user experience. It highlights the transition from a simple academic experiment to a production-grade desktop utility that runs seamlessly in the background without hogging system resources.",
            "speaker_notes": "\"The project overview highlights our end-to-end vision: Users interact naturally with their computer through simple hand signs. Whether browsing documents, dragging files, zooming in Photoshop, or closing windows, the user never touches a physical surface. The app even runs minimized in the background without dropping frame rate.\"",
            "viva_qa": [
                ("Q: How does the system handle multi-threading?", "A: One daemon thread handles webcam capture, landmark extraction, and coordinate filtering at 60 FPS, while the main thread manages the CustomTkinter GUI dashboard at throttled refresh rates.")
            ]
        },
        {
            "num": 5,
            "title": "Problem Statement & Motivation",
            "slide_text": [
                ("Hardware Fatigue & Ergonomic Injury: ", "Physical mice and trackpads contribute significantly to Carpal Tunnel Syndrome and RSI."),
                ("Sanitation & Sterile Computing: ", "Hospitals, labs, and culinary setups require hands-free computing to prevent cross-contamination."),
                ("Shortcomings of Existing Vision Mice: ", "High latency (>15ms), cursor shaking/jitter, lack of left/right click discrimination, and cursor dipping during pinch clicks."),
                ("Windows OS Restrictions: ", "Standard libraries like PyAutoGUI cannot interact with administrator (UAC) windows or game overlays.")
            ],
            "explanation": "Explicitly details why the project was built. Previous open-source attempts struggled with: (1) Jitter due to human micro-tremors and camera noise, (2) 'Click Dipping'—where curling a finger to click accidentally shifts the cursor away from the target icon, and (3) Lack of background responsiveness.",
            "speaker_notes": "\"Our motivation stems from real-world limitations. In hospital surgery rooms or industrial environments, touching mice spreads pathogens. Furthermore, users with motor impairments cannot grip hardware mice. Existing software attempts fail because the cursor shakes uncontrollably or dips when clicking. Our project directly solves each of these pain points.\"",
            "viva_qa": [
                ("Q: What is 'click dip' and how did you solve it?", "A: When bending the index finger to click, natural biomechanics causes the fingertip coordinate to drop downward by 10-20 pixels. We solved this by freezing cursor coordinates immediately upon detecting the click trigger before dispatching the event.")
            ]
        },
        {
            "num": 6,
            "title": "Existing System vs. Proposed System",
            "slide_text": [
                ("Tracking Method: ", "Existing: Color gloves / Haar Cascades | Proposed: 21 3D MediaPipe Landmarks without physical markers."),
                ("Cursor Stability: ", "Existing: Moving average (>10px jitter) | Proposed: 2-stage Hybrid (1€ + Kalman) Filter (<0.1px jitter)."),
                ("OS Event Dispatching: ", "Existing: High-level PyAutoGUI (Blocked by UAC) | Proposed: Win32 C-types `SendInput` kernel API."),
                ("Threading Model: ", "Existing: Single-threaded loop (UI freezes) | Proposed: Dual-threaded decoupled engine (60 FPS daemon)."),
                ("Click Dipping: ", "Existing: Severe cursor deflection | Proposed: Smart Target Lock (Anti-Dip Instant Pose Freeze).")
            ],
            "explanation": "A side-by-side comparative table demonstrating technical superiority over legacy and naive webcam mice implementations. It details latency, jitter, OS privilege bypass, and gesture variety.",
            "speaker_notes": "\"As demonstrated in this comparative breakdown, conventional systems rely on high-level libraries like PyAutoGUI which introduces 15ms latency and fails on administrative windows. In contrast, our proposed system employs kernel-level Win32 SendInput, custom dual-stage filtering, and instant pose freezing to achieve professional-grade cursor fidelity.\"",
            "viva_qa": [
                ("Q: Why does PyAutoGUI fail on administrative windows?", "A: PyAutoGUI uses legacy Windows user-space APIs which Windows User Account Control (UAC) isolates for security. Win32 `SendInput` with virtual desktop flags properly communicates with administrative contexts.")
            ]
        },
        {
            "num": 7,
            "title": "System Architecture & Block Diagram",
            "slide_text": [
                ("Capture Layer: ", "USB Webcam / DroidCam IP Wi-Fi stream -> OpenCV BGR-to-RGB conversion -> CLAHE contrast enhancement."),
                ("Inference Layer: ", "MediaPipe Hands extracts 21 3D spatial landmarks (X, Y, Z coordinates)."),
                ("Processing Pipeline: ", "Feature Normalization -> Pose Classifier -> ROI Coordinate Mapping -> Hybrid 1€ + Kalman Filter."),
                ("Kernel Execution: ", "Win32 `SendInput` worker queue dispatches pointer moves, clicks, scrolls, and shortcuts (`Alt+F4`)."),
                ("UI Layer: ", "CustomTkinter Dashboard renders webcam stream, tracking feedback, and sensitivity controls.")
            ],
            "explanation": "Explains the modular data-flow architecture. The visual block diagram illustrates the decoupling between the video processing pipeline and the GUI render loop, joined safely via lock-protected coordinate buffers.",
            "speaker_notes": "\"This diagram illustrates our end-to-end system architecture. Video frames are captured and enhanced via CLAHE. The dedicated 60 FPS engine extracts 21 3D hand coordinates, computes translation and scale invariance, passes coordinates through our dual-stage filter, and forwards mouse events to a reusable Win32 kernel worker queue.\"",
            "viva_qa": [
                ("Q: Why did you add CLAHE image preprocessing?", "A: Contrast Limited Adaptive Histogram Equalization (CLAHE) dynamically normalizes local image brightness, allowing accurate hand tracking even under poor room lighting or backlighting.")
            ]
        },
        {
            "num": 8,
            "title": "Technologies Used",
            "slide_text": [
                ("Core Language: ", "Python 3.8+ (High performance, C-extension binding capabilities)."),
                ("Computer Vision & ML: ", "OpenCV (Video I/O, CLAHE) & Google MediaPipe Hands (ML-based 21 3D Landmark Mesh)."),
                ("Deep Learning: ", "TensorFlow & Keras (Multi-Layer Perceptron trained on 1,800 landmark samples across 100 epochs)."),
                ("OS & Kernel Interface: ", "Win32 C-types `SendInput`, `timeBeginPeriod(1)` (1.0ms timer grain), Windows `UIAutomation`."),
                ("GUI & Visualization: ", "CustomTkinter (Modern dark theme UI), Pillow (PIL), Matplotlib & NumPy.")
            ],
            "explanation": "Details every technology, framework, and low-level API utilized in the project, justifying each tool's architectural necessity.",
            "speaker_notes": "\"Here is our technology stack: We chose Python for rapid integration, MediaPipe for state-of-the-art hand landmark detection, TensorFlow for custom gesture classification, and CustomTkinter for our modern UI. Most importantly, we leveraged native Windows Win32 C-types for kernel-level mouse dispatching and high-resolution timer boosting.\"",
            "viva_qa": [
                ("Q: Why is `timeBeginPeriod(1)` important in Windows?", "A: By default, Windows schedules threads at 15.6ms intervals, capping sleep resolution at ~64 Hz. Calling `timeBeginPeriod(1)` forces the kernel multimedia timer to 1.0ms, allowing accurate 60-120 FPS background tracking.")
            ]
        },
        {
            "num": 9,
            "title": "Hand Gesture Recognition & Control Suite",
            "slide_text": [
                ("Pointer Motion: ", "1 Finger Extended (Index) -> Maps coordinates to screen with ROI scaling."),
                ("Left Click: ", "Peace Sign (Index + Middle) -> Non-blocking left click with 5-frame debounce."),
                ("Right Click: ", "L-Shape / Gun (Thumb + Index) -> Context menu trigger with instant pose freeze."),
                ("Double Click: ", "Thumb Up Only -> Sequential double click with 30ms hardware pause."),
                ("Drag & Drop: ", "Pinch & Hold (Index + Thumb) -> Grab with 1.75x release buffer; release to drop."),
                ("Scroll & Zoom: ", "Open Palm (Slide Up/Down to Scroll) | Rock Sign (Slide Up/Down to Zoom In/Out)."),
                ("System Shortcuts: ", "Pinky Extended (Shaka Sign) -> 18-frame safety hold dispatches system `Alt + F4`."),
                ("Smart UI Hover: ", "Dwell stationary for 3 seconds -> Auto-clicks buttons via Windows Accessibility API.")
            ],
            "explanation": "Outlines the complete 9-gesture interaction vocabulary. Each gesture is designed to be ergonomic, mutually exclusive, and immune to false positive triggers through geometric hysteresis.",
            "speaker_notes": "\"Our gesture vocabulary covers 9 intuitive hand poses. Moving the cursor requires only the index finger, eliminating click jitter. Left click uses the peace sign, right click uses the L-shape, and dragging is achieved with a pinch-and-hold. We also support vertical scrolling with an open palm, zooming with the rock sign, and closing windows with a pinky hold.\"",
            "viva_qa": [
                ("Q: How do you prevent accidental triggers between similar poses?", "A: We enforce strict hierarchical evaluation: single-finger extension is mutually exclusive from multi-finger signs, and all click triggers require confirmation across debounce frame buffers.")
            ]
        },
        {
            "num": 10,
            "title": "System Workflow & Mathematical Formulation",
            "slide_text": [
                ("Step 1 (Extraction): ", "Extract 21 keypoints (x_i, y_i, z_i). Wrist (Landmark 0) serves as origin."),
                ("Step 2 (Translation Normalization): ", "Δx_i = x_i - x_0, Δy_i = y_i - y_0, Δz_i = z_i - z_0 -> Creates 63D feature vector."),
                ("Step 3 (Scale Invariance): ", "Hand size S_hand = sqrt((x_Middle_MCP - x_0)^2 + (y_Middle_MCP - y_0)^2). Normalizes for distance."),
                ("Step 4 (Pinch Calculation): ", "d_pinch = sqrt((x_8 - x_4)^2 + (y_8 - y_4)^2) < (Threshold * S_hand)."),
                ("Step 5 (Finger Extension): ", "Extension ratio = (d_tip / d_base) > 1.05 determines extended vs. curled state."),
                ("Step 6 (Neural Classification): ", "y_hat = Softmax(W_2 * ReLU(W_1 * V + b_1) + b_2).")
            ],
            "explanation": "Presents the mathematical foundation of the computer vision pipeline. The formulas guarantee that hand recognition remains invariant to where the hand is located in the camera frame and how close it is to the lens.",
            "speaker_notes": "\"This slide details our mathematical pipeline: Raw coordinates are translated relative to the wrist to ensure position invariance, and scaled by the hand's Euclidean diameter for distance invariance. Euclidean distance ratios detect pinch triggers, while our trained Multi-Layer Perceptron classifies complex signs with high confidence.\"",
            "viva_qa": [
                ("Q: Why is Middle MCP chosen for hand scale normalization?", "A: The Middle MCP (knuckle 9) forms the structural core of the metacarpal palm arch, which remains rigid and invariant regardless of whether individual fingers are curled or open.")
            ]
        },
        {
            "num": 11,
            "title": "Filtering & Coordinate Mapping",
            "slide_text": [
                ("The Jitter Challenge: ", "Human hand tremor and camera sensor noise cause 10-20px pointer shaking."),
                ("Dual-Stage Hybrid Cascade: ", "Combines Casiez's 1€ Filter with a Linear Kalman Filter."),
                ("Stage 1 (One Euro Filter): ", "Dynamic cutoff frequency based on fingertip velocity: high smoothing at low speeds, zero lag during rapid flicks."),
                ("Stage 2 (Kalman Filter): ", "Predicts state vector [x, y, dx, dy] to minimize Gaussian observation noise."),
                ("Active ROI Screen Mapping: ", "Linear interpolation from webcam ROI [x1, y1, x2, y2] to monitor resolution [0, W] x [0, H] with safety boundary margins.")
            ],
            "explanation": "Explains how the cursor achieves rock-solid stability (<0.1px jitter). A simple low-pass filter creates perceptible lag, whereas a Kalman filter alone struggles with sudden direction changes. Cascading both filters achieves the optimal balance of responsiveness and stillness.",
            "speaker_notes": "\"Filtering is crucial for usability. Naive smoothing creates heavy input lag, while no smoothing creates unreadable jitter. We solved this with a 2-stage cascade: Stage 1 uses a velocity-adaptive 1€ filter that eliminates micro-tremors when holding still. Stage 2 applies a Kalman state predictor that tracks trajectory dynamics, yielding sub-pixel accuracy.\"",
            "viva_qa": [
                ("Q: What is the purpose of the Active ROI bounding box?", "A: A standard webcam frame is wide; reaching screen corners would require moving your hand completely out of frame. The ROI defines an active central zone that maps directly to the entire display, reducing physical arm fatigue.")
            ]
        },
        {
            "num": 12,
            "title": "GUI & System Implementation",
            "slide_text": [
                ("CustomTkinter Dark Dashboard: ", "Modern, responsive interface featuring real-time video feedback with landmark skeleton overlay."),
                ("Live Telemetry Displays: ", "Real-time FPS counter, detected gesture label, click debounce status, and ROI visualization."),
                ("Collapsible Control Panel: ", "Customizable sliders for cursor sensitivity, smoothing intensity, ROI size, and click threshold."),
                ("Flexible Camera Sources: ", "Integrated camera hardware auto-scanner and DroidCam Wi-Fi IP video stream decoder (`http://IP:4747/video`)."),
                ("Background Power Optimization: ", "Throttles UI rendering to 5 FPS when minimized while maintaining dedicated 60 FPS mouse tracking.")
            ],
            "explanation": "Demonstrates the user-facing interface, showing that the system is fully configured and ready for consumer deployment with intuitive controls and customizable ergonomics.",
            "speaker_notes": "\"Our implementation includes a sleek CustomTkinter dashboard. It features live landmark visualizers, telemetry displays, and real-time sensitivity sliders. Users can switch between physical webcams and DroidCam Wi-Fi streams. When minimized to the taskbar, the app drops GUI redraws to 5 FPS to preserve battery life while tracking continues at 60 FPS.\"",
            "viva_qa": [
                ("Q: Why support DroidCam Wi-Fi streams?", "A: Many laptops have poor 480p/720p webcams. DroidCam allows users to use their smartphone's high-definition 1080p 60 FPS camera wirelessly without installing special Windows virtual camera drivers.")
            ]
        },
        {
            "num": 13,
            "title": "Results & Performance Evaluation",
            "slide_text": [
                ("Deep Learning Performance: ", "100-Epoch Training: 99.7% training accuracy, 99.4% validation accuracy, categorical loss dropped to 0.038."),
                ("Evolutionary Milestones: ", "Accuracy increased from 72.4% (Day 1) to 99.9% (Day 12); pointer jitter reduced from 18.5 px to <0.1 px."),
                ("System Latency: ", "End-to-end processing pipeline latency reduced from 14.2 ms down to 0.7 ms operating at 60 FPS."),
                ("Live Similarity Verification: ", "Real-time webcam gestures consistently score >95% similarity against training templates (well above 90% threshold).")
            ],
            "explanation": "Presents the quantitative validation of the project using empirical metrics gathered across 12 development milestones, including neural network loss/accuracy graphs and real-time live similarity benchmarks.",
            "speaker_notes": "\"Our empirical results confirm outstanding performance. Our neural network converges cleanly across 100 epochs to 99.7% accuracy with near-zero loss. Over our development cycle, pointer jitter dropped from 18.5 pixels to under 0.1 pixels, and total processing latency dropped to 0.7 milliseconds, ensuring instant responsiveness.\"",
            "viva_qa": [
                ("Q: How did you measure 0.7 ms latency?", "A: Latency is computed using Windows high-resolution performance counters (`QueryPerformanceCounter`), timing landmark extraction, feature normalization, filter updates, and coordinate dispatching per frame.")
            ]
        },
        {
            "num": 14,
            "title": "Advantages, Applications & Limitations",
            "slide_text": [
                ("Key Advantages: ", "Zero hardware cost, sub-millisecond latency, zero-jitter precision, full 9-gesture suite, and background execution."),
                ("Primary Applications: ", "Sterile medical surgical suites, assistive tech for motor-disabled users, hygienic public kiosks, interactive presentations, and gaming."),
                ("System Limitations: ", "Performance degrades in extreme dark or intense backlight; requires clear line of sight; continuous arm elevation can cause fatigue without desk rest.")
            ],
            "explanation": "A balanced, objective evaluation of the project's practical utility. It highlights key commercial and humanitarian use-cases while honestly addressing current limitations.",
            "speaker_notes": "\"The advantages of our system include zero hardware cost, rock-solid stability, and accessibility. Key applications include operating theatres where surgeons cannot touch peripherals, public interactive kiosks, and assistive computing. Current limitations include sensitivity to extreme darkness and potential arm fatigue during prolonged use, which can be mitigated with ergonomic arm positioning.\"",
            "viva_qa": [
                ("Q: How can arm fatigue ('Gorilla Arm' effect) be minimized?", "A: By tuning the sensitivity slider and ROI bounding box, users can control the entire screen with small hand and wrist movements while resting their elbow on a desk surface.")
            ]
        },
        {
            "num": 15,
            "title": "Conclusion & Future Scope",
            "slide_text": [
                ("Project Conclusion: ", "Successfully engineered an ultra-responsive, touchless AI virtual mouse that matches physical mouse fidelity."),
                ("Key Achievements: ", "Sub-millisecond processing (0.7ms), 99.7% ML accuracy, dual-stage 1€ + Kalman filtering, and kernel-level Windows event execution."),
                ("Future Enhancement 1: ", "Multi-Hand & Bimanual Gestures (One hand navigation, second hand shortcuts/chording)."),
                ("Future Enhancement 2: ", "Cross-Platform Driver Support for Linux (X11/Wayland) and macOS (Quartz Event Taps)."),
                ("Future Enhancement 3: ", "Eye-Gaze Fusion (Webcam iris tracking for rapid coarse targeting + finger pinch for micro-clicking).")
            ],
            "explanation": "Concludes the presentation by summarizing the engineering achievements and outlining exciting future research directions for multi-modal spatial computing.",
            "speaker_notes": "\"To conclude, AI Gesture Mouse demonstrates that high-performance, touchless computing is achievable using ordinary webcams and intelligent software engineering. In the future, we plan to implement bimanual two-hand interactions, cross-platform Linux/macOS support, and hybrid eye-tracking fusion. Thank you, and I am now open to any questions.\"",
            "viva_qa": [
                ("Q: How would eye-gaze fusion improve the system?", "A: Eye gaze quickly shifts the pointer to the general area of interest on the screen, while hand gestures perform precise clicking and fine adjustments, creating a natural multimodal interface similar to Apple Vision Pro.")
            ]
        }
    ]

    for s in slides_content:
        add_h1(f"Slide {s['num']}: {s['title']}")

        # Slide content table / bullets
        add_h2("📌 Slide Content (Bullet Points for PPT):")
        for pref, txt in s['slide_text']:
            add_bullet(pref, txt)

        add_h2("📖 Detailed Technical Explanation:")
        p_exp = doc.add_paragraph()
        p_exp.paragraph_format.space_after = Pt(4)
        p_exp.add_run(s['explanation'])

        add_h2("🎙️ Presenter Script (What to Say):")
        p_spk = doc.add_paragraph()
        p_spk.paragraph_format.left_indent = Inches(0.2)
        p_spk.paragraph_format.space_after = Pt(4)
        r_spk = p_spk.add_run(s['speaker_notes'])
        r_spk.font.italic = True
        r_spk.font.color.rgb = SLATE

        add_h2("💡 Probable Viva / Evaluation Q&A:")
        for q, a in s['viva_qa']:
            add_bullet(f"{q} ", a)

        doc.add_paragraph() # Spacer between slides

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "results", "documents")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "AI_Gesture_Mouse_PPT_Detailed_Guide.docx")
    doc.save(output_path)
    print(f"[+] Successfully generated PPT Detailed Guide: {output_path}")

if __name__ == "__main__":
    create_ppt_detailed_document()
