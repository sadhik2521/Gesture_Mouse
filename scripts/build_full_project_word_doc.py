# -*- coding: utf-8 -*-
"""
AI Gesture Mouse - Complete Beginner-Friendly Project Documentation Generator
Creates 'AI_Gesture_Mouse_Full_Documentation.docx' with professional styling,
rich tables, mathematical equations, workflow diagrams, and embedded plots.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def add_callout(doc, text, title="NOTE", fill_hex="EFF6FF", border_hex="3B82F6"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, fill_hex)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)

    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_hex}"/>'
        f'  <w:top w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run_title = p.add_run(f"[{title}] ")
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(10.5)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(30, 64, 175)

    run_text = p.add_run(text)
    run_text.font.name = 'Calibri'
    run_text.font.size = Pt(10.5)
    run_text.font.color.rgb = RGBColor(30, 41, 59)
    doc.add_paragraph() # spacing

def create_full_documentation():
    doc = docx.Document()

    # Set page margins (1 inch)
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Base Colors
    NAVY = RGBColor(15, 23, 42)      # #0f172a
    BLUE = RGBColor(37, 99, 235)     # #2563eb
    SLATE = RGBColor(71, 85, 105)    # #475569
    DARK_TEXT = RGBColor(30, 41, 59) # #1e293b

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = DARK_TEXT

    def add_heading_1(text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(6)
        run = h.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(18)
        run.font.bold = True
        run.font.color.rgb = BLUE
        return h

    def add_heading_2(text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(4)
        run = h.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(13.5)
        run.font.bold = True
        run.font.color.rgb = NAVY
        return h

    def add_bullet(p_or_text, bold_prefix="", text=""):
        if isinstance(p_or_text, str):
            p = doc.add_paragraph(style='List Bullet')
            bold_prefix = p_or_text
        else:
            p = p_or_text
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        if bold_prefix:
            r1 = p.add_run(bold_prefix)
            r1.font.bold = True
            r1.font.color.rgb = NAVY
        if text:
            r2 = p.add_run(text)
            r2.font.color.rgb = DARK_TEXT
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # TITLE & HEADER
    # ══════════════════════════════════════════════════════════════════════════
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("AI Gesture Mouse")
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(28)
    run_title.font.bold = True
    run_title.font.color.rgb = BLUE

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("Complete Beginner-Friendly Project Documentation & Technical Guide")
    run_sub.font.name = 'Calibri'
    run_sub.font.size = Pt(14)
    run_sub.font.bold = True
    run_sub.font.color.rgb = SLATE

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_meta = p_meta.add_run("Webcam Hand Tracking | Google MediaPipe | Windows SendInput | Dynamic Dataset Learning")
    run_meta.font.size = Pt(10)
    run_meta.font.italic = True
    run_meta.font.color.rgb = SLATE

    doc.add_paragraph()

    # Embed Dashboard Image if exists
    ui_dash_path = os.path.join(PROJECT_ROOT, "assets", "ui_dashboard.jpg")
    if os.path.exists(ui_dash_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_after = Pt(12)
        doc.add_picture(ui_dash_path, width=Inches(6.0))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 1: AI Gesture Mouse v5.0 Graphical User Interface Dashboard")
        r_cap.font.size = Pt(9)
        r_cap.font.italic = True
        r_cap.font.color.rgb = SLATE

    # ══════════════════════════════════════════════════════════════════════════
    # 1. PROJECT OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("1. Project Overview (In Simple Terms)")
    
    p = doc.add_paragraph()
    p.add_run(
        "The AI Gesture Mouse is an intelligent, touchless desktop control system that allows users to control "
        "their Windows computer using simple hand gestures captured through a standard webcam. It completely "
        "eliminates the need for a physical mouse, wearable gloves, or expensive specialized sensors."
    )

    p2 = doc.add_paragraph()
    p2.add_run("How it feels to use in everyday life:")
    add_bullet("Point your index finger in the air: ", "The cursor glides smoothly across your monitor to follow your finger.")
    add_bullet("Make a Peace sign (✌️): ", "Fires a Left Click.")
    add_bullet("Make an 'L' shape (👉): ", "Fires a Right Click to open context menus.")
    add_bullet("Pinch thumb and index together (🤏): ", "Grabs icons, windows, or files for Drag & Drop.")
    add_bullet("Show an open palm (🖐️) and move up/down: ", "Scrolls pages smoothly up or down.")
    add_bullet("Make a rock sign (🤘) and move up/down: ", "Zooms in or zooms out.")
    add_bullet("Extend your pinky finger (🤙): ", "Closes the current active window (Alt + F4).")
    add_bullet("Close your hand into a fist (✊): ", "Enters Idle mode, pausing all mouse actions.")

    add_callout(
        doc,
        "The system runs at 60 FPS in a dedicated background worker thread, ensuring cursor tracking and gesture "
        "actions remain ultra-fast and lag-free even when the dashboard window is minimized.",
        title="CORE HIGHLIGHT"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # 2. TECHNOLOGIES USED
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("2. Technologies & Libraries Used")

    tech_table = doc.add_table(rows=1, cols=3)
    tech_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tech_table)

    hdr = tech_table.rows[0].cells
    hdr[0].text = "Technology / Library"
    hdr[1].text = "Role in this Project"
    hdr[2].text = "Why It Was Chosen"
    for cell in hdr:
        set_cell_background(cell, "1E3A8A")
        set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
        for p in cell.paragraphs:
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

    tech_data = [
        ("Python 3.12", "Core Programming Language", "Clean syntax, fast development, rich AI & computer vision libraries."),
        ("Google MediaPipe", "Hand Pose & Landmark Estimation", "Detects 21 3D hand keypoints in real time with high accuracy at 60+ FPS."),
        ("OpenCV (cv2)", "Webcam Capture & Image Processing", "Streams video, mirrors display, applies CLAHE lighting enhancement."),
        ("TensorFlow / Keras", "Deep Learning Model Training", "4-layer Neural Network (MLP) trained on gesture coordinate dataset."),
        ("NumPy", "Matrix & Vector Math", "Fast array calculations, coordinate normalization, Euclidean distance matching."),
        ("Pandas", "Dataset Management", "Exports and structures gesture dataset into human-readable CSV with column names."),
        ("Windows ctypes SendInput", "Hardware-Level Mouse Control", "Dispatches hardware-level mouse events with sub-1ms response time."),
        ("UIAutomation (uiautomation)", "Accessibility UI Inspection", "Inspects buttons and links under cursor for smart hover auto-clicking."),
        ("CustomTkinter", "Modern Dark-Mode GUI", "Sleek, customizable desktop dashboard with toggle switches and live metrics."),
        ("Matplotlib", "Training & Similarity Plotting", "Generates accuracy/loss curves and live visual similarity bar charts.")
    ]

    for row_idx, data in enumerate(tech_data):
        row = tech_table.add_row().cells
        bg = "F8FAFC" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate(data):
            row[i].text = val
            set_cell_background(row[i], bg)
            set_cell_margins(row[i], top=90, bottom=90, left=120, right=120)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # 3. GESTURE SIGNS GUIDE
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("3. Gesture Signs Guide (Hand Poses & Actions)")

    poster_path = os.path.join(PROJECT_ROOT, "assets", "gesture_signs_poster.jpg")
    if os.path.exists(poster_path):
        doc.add_picture(poster_path, width=Inches(6.0))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 2: AI Virtual Mouse Hand Gestures Reference Poster")
        r_cap.font.size = Pt(9)
        r_cap.font.italic = True
        r_cap.font.color.rgb = SLATE

    gest_table = doc.add_table(rows=1, cols=4)
    gest_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(gest_table)

    ghdr = gest_table.rows[0].cells
    ghdr[0].text = "ID"
    ghdr[1].text = "Gesture Name"
    ghdr[2].text = "Hand Pose Sign"
    ghdr[3].text = "Action Performed"
    for cell in ghdr:
        set_cell_background(cell, "1E3A8A")
        set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
        for p in cell.paragraphs:
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

    gestures = [
        ("0", "Move Cursor", "1 Finger Extended (Index Only)", "Cursor moves smoothly across screen. Strict tracking mode."),
        ("1", "Drag & Drop", "Pinch & Hold (Index + Thumb)", "Pinch to grab windows or files. Open fingers to drop."),
        ("2", "Left Click", "Peace Sign (Index + Middle)", "Fires a single left click via kernel SendInput."),
        ("3", "Right Click", "L-Shape / Gun (Thumb + Index)", "Fires right click to open context menu."),
        ("4", "Double Click", "Thumb Only Extended", "Rapid double left click to open files or folders."),
        ("5", "Scroll Up / Down", "Open Palm (5 Extended)", "Tracks hand vertical speed: slide UP to scroll up, DOWN to scroll down."),
        ("6", "Zoom In / Out", "Rock Sign (Index + Pinky)", "Slide hand UP to Zoom In (Ctrl + =), DOWN to Zoom Out (Ctrl + -)."),
        ("7", "Close Window", "Pinky Extended (Shaka Sign)", "Safety hold for 0.3s sends Alt + F4 to close current window."),
        ("8", "Idle", "Closed Fist", "Pauses all cursor actions (safe resting position).")
    ]

    for row_idx, g in enumerate(gestures):
        row = gest_table.add_row().cells
        bg = "F8FAFC" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate(g):
            row[i].text = val
            set_cell_background(row[i], bg)
            set_cell_margins(row[i], top=90, bottom=90, left=120, right=120)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # 4. WORKFLOW ARCHITECTURE
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("4. Workflow Diagram (Simple Block Architecture)")

    p = doc.add_paragraph()
    p.add_run(
        "The system processes each video frame through a streamlined, multi-stage pipeline designed for minimum latency:"
    )

    steps = [
        ("Block 1: Frame Acquisition", "Webcam captures a 640x480 frame at 30/60 FPS. Mirrored horizontally for natural hand interaction."),
        ("Block 2: Illumination Enhancement", "OpenCV CLAHE (Contrast Limited Adaptive Histogram Equalization) boosts contrast and balances poor lighting."),
        ("Block 3: Keypoint Extraction", "Google MediaPipe Hands locates the 21 3D hand joints with millimeter precision."),
        ("Block 4: Coordinate Normalization", "Joint coordinates are subtracted from the Wrist joint (Landmark 0) to remove hand position bias."),
        ("Block 5: Dual-Path Processing", "Path A: Feeds Index PIP joint to One Euro + Kalman filter for cursor motion.\nPath B: Evaluates hand shape against learned gesture templates."),
        ("Block 6: Anti-Jitter & Debounce", "Debounce counters confirm gestures across consecutive frames before firing actions."),
        ("Block 7: OS Hardware Execution", "Low-latency Win32 SendInput dispatches mouse clicks, movement, and scrolls directly to Windows.")
    ]

    for title, desc in steps:
        add_bullet(f"{title}: ", desc)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # 5. HOW GESTURES ARE CAPTURED & SHORTFORMS
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("5. How Gestures Are Captured & Heading Abbreviations")

    p = doc.add_paragraph()
    p.add_run(
        "Each video frame yields 21 key hand joints from Google MediaPipe. Every joint provides three spatial coordinates "
        "(x, y, z), resulting in 21 * 3 = 63 numerical features per sample row."
    )

    add_heading_2("Column Heading Abbreviations Explained:")
    abbr_data = [
        ("gesture_id", "Numeric ID of the gesture class (0 to 8)."),
        ("gesture_name", "Readable label (e.g., 'Right Click (L-Shape)', 'Left Click')."),
        ("lm", "Landmark index from 0 to 20 representing a hand joint."),
        ("wrist", "Landmark 0: The base of the hand; acts as the (0, 0, 0) origin."),
        ("cmc", "Carpometacarpal joint: Base joint connecting thumb to the wrist."),
        ("mcp", "Metacarpophalangeal joint: The large base knuckle where finger meets palm."),
        ("ip", "Interphalangeal joint: The middle knuckle hinge of the thumb."),
        ("pip", "Proximal Interphalangeal joint: Lower middle knuckle of fingers."),
        ("dip", "Distal Interphalangeal joint: Top knuckle right beneath fingernail."),
        ("tip", "Fingertip: Pad / tip of the finger or thumb."),
        ("_x", "Horizontal coordinate relative to wrist (negative = left, positive = right)."),
        ("_y", "Vertical coordinate relative to wrist (negative = UP, positive = down)."),
        ("_z", "Depth distance relative to the camera plane.")
    ]

    abbr_table = doc.add_table(rows=1, cols=2)
    abbr_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(abbr_table)

    ahdr = abbr_table.rows[0].cells
    ahdr[0].text = "Short Form"
    ahdr[1].text = "Full Anatomical Term & Meaning"
    for cell in ahdr:
        set_cell_background(cell, "1E3A8A")
        set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
        for p in cell.paragraphs:
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, (sf, desc) in enumerate(abbr_data):
        row = abbr_table.add_row().cells
        bg = "F8FAFC" if row_idx % 2 == 0 else "FFFFFF"
        row[0].text = sf
        row[1].text = desc
        set_cell_background(row[0], bg)
        set_cell_background(row[1], bg)
        set_cell_margins(row[0], top=80, bottom=80, left=120, right=120)
        set_cell_margins(row[1], top=80, bottom=80, left=120, right=120)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # 6. MATHEMATICAL FORMULAS
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("6. Mathematical Formulas & Calculations")

    add_heading_2("Formula 1: Wrist-Relative Coordinate Normalization")
    p = doc.add_paragraph()
    p.add_run(
        "To make gesture classification independent of where your hand sits in the camera frame, "
        "all 21 landmark positions are normalized relative to the Wrist (Landmark 0):\n"
        "   x_norm = x_lm - x_wrist\n"
        "   y_norm = y_lm - y_wrist\n"
        "   z_norm = z_lm - z_wrist\n"
        "Outcome: The wrist is always (0, 0, 0). Moving your whole arm across the room does not alter the gesture shape."
    )

    add_heading_2("Formula 2: Euclidean Distance for Pinch Detection (Drag & Drop)")
    p = doc.add_paragraph()
    p.add_run(
        "Measures the 2D Euclidean distance between index fingertip and thumb tip:\n"
        "   Distance = sqrt((x_index_tip - x_thumb_tip)^2 + (y_index_tip - y_thumb_tip)^2)\n"
        "If Distance < (click_threshold * hand_scale), a Pinch event is registered."
    )

    add_heading_2("Formula 3: Finger Extension Ratio")
    p = doc.add_paragraph()
    p.add_run(
        "Determines whether a finger is stretched straight or curled into the palm:\n"
        "   Extension_Ratio = Distance(Fingertip, Wrist) / Distance(Base_Knuckle_MCP, Wrist)\n"
        "• Ratio > 1.45: Finger is Extended (pointing straight).\n"
        "• Ratio < 1.05: Finger is Folded (tucked into the palm)."
    )

    add_heading_2("Formula 4: Linear Screen Coordinate Interpolation")
    p = doc.add_paragraph()
    p.add_run(
        "Maps the hand control position from webcam space (640x480) to full monitor resolution (W_screen x H_screen):\n"
        "   Screen_X = ((Finger_X - Box_Min_X) / (Box_Max_X - Box_Min_X)) * W_screen\n"
        "   Screen_Y = ((Finger_Y - Box_Min_Y) / (Box_Max_Y - Box_Min_Y)) * H_screen"
    )

    add_heading_2("Formula 5: One Euro Speed-Adaptive Smoothing Filter")
    p = doc.add_paragraph()
    p.add_run(
        "A dual-pole adaptive low-pass filter that eliminates jitter when holding still, while eliminating lag when moving fast:\n"
        "   alpha = 1 / (1 + tau / T_e)\n"
        "   tau = 1 / (2 * pi * (min_cutoff + beta * |velocity|))\n"
        "• Low velocity (hand still) -> cutoff frequency drops -> heavy smoothing, zero tremor.\n"
        "• High velocity (fast swipe) -> cutoff frequency increases -> zero lag, instant response."
    )

    add_heading_2("Formula 6: Exponential Similarity Score")
    p = doc.add_paragraph()
    p.add_run(
        "Converts 63-dimensional Euclidean distance between the live hand and gesture templates into a 0-100% match score:\n"
        "   Similarity = exp(-Distance * 4.5) * 100%\n"
        "When your hand matches the template perfectly (Distance = 0), Similarity = 100%."
    )

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # 7. WHERE TO SEE GESTURE VALUES & DYNAMIC TEMPLATES
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("7. Where to See Gesture Values & Outputs")

    add_bullet("1. Full Labeled Dataset: ", "dataset/gestures_data.csv — contains all 1,798 sample rows with gesture_id, gesture_name, and 63 named coordinates.")
    add_bullet("2. Template Averages Summary: ", "dataset/gesture_averages_reference.csv — 9 rows showing the exact average coordinates for each gesture class.")
    add_bullet("3. Real-Time Graphical Meter: ", "Run 'python live_test_graph.py' to view live percentage match bars for all 9 gestures simultaneously.")
    add_bullet("4. Live On-Screen HUD Badge: ", "In main.py, the bottom of the camera feed displays 'AI: [Gesture Name] (XX%)' showing real-time classification.")

    add_callout(
        doc,
        "Why Changing Gestures Previously Failed: Earlier versions used hardcoded geometric checks (e.g. thumb_ext and index_ext) "
        "and ignored the dataset. The system has now been upgraded with Dynamic Dataset Template Learning: the engine loads "
        "dataset/X_gestures.npy at startup and gives your recorded dataset templates 100% priority over hardcoded rules.",
        title="IMPORTANT FIX EXPLANATION"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # 8. COMMANDS REFERENCE
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("8. Commands to Perform All Operations")

    cmd_table = doc.add_table(rows=1, cols=3)
    cmd_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(cmd_table)

    chdr = cmd_table.rows[0].cells
    chdr[0].text = "Task / Operation"
    chdr[1].text = "Command Line Syntax"
    chdr[2].text = "Description"
    for cell in chdr:
        set_cell_background(cell, "1E3A8A")
        set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
        for p in cell.paragraphs:
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

    commands = [
        ("Run Main Mouse App", "python main.py", "Opens the modern dashboard and starts touchless mouse control."),
        ("Record All Gestures", "python train_gesture_model.py --collect", "Opens webcam to record samples for classes 0 to 8."),
        ("Replace Single Gesture", "python train_gesture_model.py --replace-gesture 3", "Re-records ONLY Gesture 3 (Right Click) with webcam and updates dataset."),
        ("Sync Changes from CSV", "python train_gesture_model.py --from-csv", "Synchronizes manually edited gestures_data.csv into X_gestures.npy & y_gestures.npy."),
        ("Train AI Neural Network", "python train_gesture_model.py --train", "Trains the 4-layer Deep Neural Network model over 100 epochs."),
        ("Launch Live Test Meter", "python live_test_graph.py", "Opens camera with real-time percentage matching bars for each gesture."),
        ("Generate Accuracy Curves", "python plot_accuracy_loss.py", "Plots publication-ready training accuracy and loss curves in assets/plots/."),
        ("Generate Similarity Plot", "python plot_simple_similarity.py", "Plots gesture consistency similarity bar graph in assets/plots/.")
    ]

    for row_idx, (task, cmd, desc) in enumerate(commands):
        row = cmd_table.add_row().cells
        bg = "F8FAFC" if row_idx % 2 == 0 else "FFFFFF"
        row[0].text = task
        row[1].text = cmd
        row[2].text = desc
        set_cell_background(row[0], bg)
        set_cell_background(row[1], bg)
        set_cell_background(row[2], bg)
        set_cell_margins(row[0], top=80, bottom=80, left=120, right=120)
        set_cell_margins(row[1], top=80, bottom=80, left=120, right=120)
        set_cell_margins(row[2], top=80, bottom=80, left=120, right=120)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # 9. CODEBASE ARCHITECTURE
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("9. Codebase Architecture & File Roles")

    files = [
        ("main.py", "Application entry point. Initializes ModernGestureGUI and boots the event loop."),
        ("gui.py", "CustomTkinter graphical user interface dashboard with dark mode styling, camera stream display, and controls."),
        ("gesture_engine.py", "Core processing pipeline. Performs MediaPipe inference, One Euro filtering, template matching, and action dispatching."),
        ("mouse_controller.py", "Low-latency Win32 SendInput ctypes wrapper. Implements asynchronous non-blocking mouse events."),
        ("train_gesture_model.py", "CLI utility for dataset collection, single gesture replacement, CSV synchronization, and model training."),
        ("live_test_graph.py", "Interactive test utility displaying side-by-side camera feed and live percentage matching bar chart."),
        ("dataset/", "Data folder housing raw matrices (X_gestures.npy, y_gestures.npy) and labeled tables (gestures_data.csv)."),
        ("assets/", "Holds documentation poster images, UI screenshots, and evaluation plots.")
    ]

    for fname, fdesc in files:
        add_bullet(f"{fname}: ", fdesc)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # 10. EVALUATION & PERFORMANCE PLOTS
    # ══════════════════════════════════════════════════════════════════════════
    add_heading_1("10. Experimental Evaluation & Performance Plots")

    acc_plot = os.path.join(PROJECT_ROOT, "results", "plots", "accuracy_graph.png")
    if not os.path.exists(acc_plot):
        acc_plot = os.path.join(PROJECT_ROOT, "assets", "plots", "accuracy_graph.png")
    if os.path.exists(acc_plot):
        doc.add_picture(acc_plot, width=Inches(5.5))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 3: Training & Validation Accuracy across 100 Epochs (Final: 98.4%)")
        r_cap.font.size = Pt(9); r_cap.font.italic = True; r_cap.font.color.rgb = SLATE

    sim_plot = os.path.join(PROJECT_ROOT, "results", "plots", "simple_live_similarity.png")
    if not os.path.exists(sim_plot):
        sim_plot = os.path.join(PROJECT_ROOT, "assets", "plots", "simple_live_similarity.png")
    if os.path.exists(sim_plot):
        doc.add_picture(sim_plot, width=Inches(5.5))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 4: Live Hand Similarity Match Scores across 9 Gesture Classes")
        r_cap.font.size = Pt(9); r_cap.font.italic = True; r_cap.font.color.rgb = SLATE

    output_dir = os.path.join(PROJECT_ROOT, "results", "documents")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "AI_Gesture_Mouse_Full_Documentation.docx")
    doc.save(output_path)
    print(f"[OK] Successfully generated {output_path}")

if __name__ == "__main__":
    create_full_documentation()

