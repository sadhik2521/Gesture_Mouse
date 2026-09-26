from PIL import Image, ImageDraw, ImageFont
import os

def generate_gesture_guide():
    width, height = 1280, 800
    bg_color = (13, 24, 41)  # #0d1829 Dark Theme
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Header Banner
    draw.rectangle([(0, 0), (width, 80)], fill=(15, 34, 64))
    
    # Try loading fonts, fallback to default if needed
    try:
        title_font = ImageFont.truetype("arial.ttf", 32)
        sub_font   = ImageFont.truetype("arial.ttf", 16)
        card_title = ImageFont.truetype("arialbd.ttf", 20)
        card_desc  = ImageFont.truetype("arial.ttf", 15)
        card_tag   = ImageFont.truetype("arialbd.ttf", 14)
    except:
        title_font = card_title = card_desc = card_tag = sub_font = ImageFont.load_default()

    # Header text
    draw.text((30, 20), "⚡ AI GESTURE MOUSE v5.0 — COMPLETE GESTURE GUIDE", fill=(56, 189, 248), font=title_font)
    draw.text((30, 56), "Streamlined Touchless Control Scheme with Dual-Thread Processing", fill=(148, 163, 184), font=sub_font)

    gestures = [
        {"icon": "☘️", "name": "Move Cursor", "pose": "1 Finger (Index Only)", "action": "Moves mouse cursor across screen with Hybrid Precision Filter", "color": (56, 189, 248)},
        {"icon": "🤏", "name": "Drag & Drop", "pose": "Pinch & Hold (Idx+Thumb)", "action": "Pinch Index & Thumb to grab/drag. Open fingers to Drop", "color": (168, 85, 247)},
        {"icon": "✌️", "name": "Left Click", "pose": "Peace Sign (Index+Middle)", "action": "Single Left Click via non-blocking SendInput kernel API", "color": (52, 211, 153)},
        {"icon": "👆", "name": "Right Click", "pose": "L-Shape (Thumb+Index)", "action": "Right Click context menu with instant pose freeze", "color": (251, 146, 60)},
        {"icon": "👍", "name": "Double Click", "pose": "Thumb Only", "action": "Fast sequential left clicks with hardware pause", "color": (250, 204, 21)},
        {"icon": "🖐", "name": "Scroll Up / Down", "pose": "Open Palm (5 Fingers)", "action": "Slide hand UP for Scroll Up, DOWN for Scroll Down", "color": (56, 189, 248)},
        {"icon": "🤘", "name": "Zoom In / Out", "pose": "Rock Sign (Index+Pinky)", "action": "Slide hand UP (Zoom In Ctrl+=), DOWN (Zoom Out Ctrl+-)", "color": (236, 72, 153)},
        {"icon": "🤙", "name": "Close Window", "pose": "Pinky Extended (Shaka)", "action": "18-frame (~300ms) safety hold dispatches system Alt+F4", "color": (244, 63, 94)},
        {"icon": "🕐", "name": "Smart UI Hover", "pose": "Point & Hold (UI Hover 3s)", "action": "Hover 3s over UI element to auto-click (Accessibility Tree)", "color": (163, 230, 53)},
    ]

    # Grid layout: 3 rows of 3 cards
    cols = 3
    card_w, card_h = 380, 220
    start_x, start_y = 50, 100
    gap_x, gap_y = 20, 20
    
    # Increase image height to fit 3 rows
    height = 100 + 3 * (card_h + gap_y) + 20
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (width, 80)], fill=(15, 34, 64))
    draw.text((30, 20), "⚡ AI GESTURE MOUSE v5.0 — COMPLETE GESTURE GUIDE", fill=(56, 189, 248), font=title_font)
    draw.text((30, 56), "Streamlined Touchless Control Scheme with Dual-Thread Processing", fill=(148, 163, 184), font=sub_font)

    for i, g in enumerate(gestures):
        r = i // cols
        c = i % cols
        x = start_x + c * (card_w + gap_x)
        y = start_y + r * (card_h + gap_y)

        # Card Background
        draw.rounded_rectangle([(x, y), (x + card_w, y + card_h)], radius=12, fill=(19, 35, 60), outline=(30, 58, 95), width=2)
        
        # Header strip inside card
        draw.rounded_rectangle([(x + 10, y + 10), (x + card_w - 10, y + 55)], radius=8, fill=(11, 22, 40))
        
        # Gesture Name & Pose
        draw.text((x + 20, y + 18), f"{g['icon']} {g['name']}", fill=g['color'], font=card_title)
        draw.text((x + 20, y + 68), f"Pose: {g['pose']}", fill=(203, 213, 225), font=card_tag)

        # Divider line inside card
        draw.line([(x + 20, y + 95), (x + card_w - 20, y + 95)], fill=(30, 58, 95), width=1)

        # Action description wrapped
        action_text = g['action']
        words = action_text.split()
        lines = []
        curr_line = ""
        for word in words:
            if len(curr_line + " " + word) <= 35:
                curr_line += (" " if curr_line else "") + word
            else:
                lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)

        ly = y + 115
        for line in lines:
            draw.text((x + 20, ly), line, fill=(148, 163, 184), font=card_desc)
            ly += 22

        # Status badge at bottom of card
        draw.rounded_rectangle([(x + 20, y + card_h - 45), (x + card_w - 20, y + card_h - 15)], radius=6, fill=(15, 45, 75))
        draw.text((x + 32, y + card_h - 38), f"Action: {g['name']}", fill=g['color'], font=card_tag)

    # Save image
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    out_path = os.path.join(project_root, "assets", "gesture_guide_v5.jpg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, quality=95)
    print(f"Generated {out_path} successfully!")

if __name__ == "__main__":
    generate_gesture_guide()
