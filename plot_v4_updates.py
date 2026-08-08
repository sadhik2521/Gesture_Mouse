import numpy as np
import matplotlib.pyplot as plt
import os
import time

def plot_v4_updates():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "v4_improvements.png")

    fig, axs = plt.subplots(1, 2, figsize=(14, 5), dpi=300)

    # --- Plot 1: Thumbs Up Target Lock (Anti-Dip) ---
    ax1 = axs[0]
    frames = np.arange(0, 50)
    
    # Simulate the index finger dipping when curling into a fist
    # Starts at 500px, dips down to 550px over 15 frames
    base_y = 500.0
    raw_y = np.full(50, base_y)
    dip = np.linspace(0, 80, 20)  # Dip down 80 pixels
    raw_y[20:40] = base_y + dip
    raw_y[40:] = base_y + 80
    
    # Filtered Y (with 10-frame time machine)
    # The gesture is recognized at frame 35. It instantly rewinds to frame 25 (10 frames ago)
    fixed_y = np.copy(raw_y)
    gesture_trigger_frame = 35
    rewind_frame = 25
    
    fixed_y[gesture_trigger_frame:] = raw_y[rewind_frame]
    
    ax1.plot(frames, raw_y, label="Raw Index Finger (Dips during fist)", color="red", alpha=0.5, linestyle="--", linewidth=2)
    ax1.plot(frames[:gesture_trigger_frame], fixed_y[:gesture_trigger_frame], color="#38bdf8", linewidth=3)
    ax1.plot(frames[gesture_trigger_frame:], fixed_y[gesture_trigger_frame:], color="#34d399", linewidth=3, label="Smart Target Lock")
    
    ax1.axvline(x=gesture_trigger_frame, color='white', linestyle=':', alpha=0.5)
    ax1.annotate("Double Click Triggered\nRewinds 10 frames!", xy=(gesture_trigger_frame, fixed_y[gesture_trigger_frame]), 
                 xytext=(gesture_trigger_frame - 15, fixed_y[gesture_trigger_frame] - 30),
                 arrowprops=dict(facecolor='white', arrowstyle="->", connectionstyle="arc3,rad=-0.2"), color="white", fontweight="bold")
    
    ax1.set_title("Thumbs-Up Target Lock (Anti-Dip Engine)", color="white", fontsize=14, pad=15)
    ax1.set_xlabel("Frames", color="silver")
    ax1.set_ylabel("Cursor Y Position (px)", color="silver")
    ax1.set_facecolor("#13233c")
    ax1.tick_params(colors="silver")
    ax1.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="white")
    ax1.invert_yaxis()

    # --- Plot 2: Smart UI Component Tracking ---
    ax2 = axs[1]
    time_sec = np.linspace(0, 4, 100)
    
    # Simulated bounding box of a UI Component
    ui_top, ui_bottom = 380, 500
    
    # Cursor wandering inside the UI component
    cursor_wander = 440 + 35 * np.sin(time_sec * 4) + np.random.normal(0, 5, 100)
    
    # Old Dwell Click progress (resets if cursor moves > 20px)
    old_progress = np.zeros(100)
    p = 0
    ref_y = cursor_wander[0]
    for i in range(100):
        if abs(cursor_wander[i] - ref_y) > 20:
            p = 0
            ref_y = cursor_wander[i]
        else:
            p += 0.04
        old_progress[i] = p * 100
        
    # New UI component progress (steadily increases as long as it's inside the bounds)
    new_progress = np.zeros(100)
    p = 0
    for i in range(100):
        if ui_top <= cursor_wander[i] <= ui_bottom:
            p += (100 / 75) # reaches 100 in 3 seconds (75 frames at 25fps)
        else:
            p = 0
        new_progress[i] = min(100, p)
        
    ax2.plot(time_sec, cursor_wander, color="#a855f7", label="Cursor Y (Wandering inside Button)", linewidth=2)
    ax2.fill_between(time_sec, ui_top, ui_bottom, color="#1e293b", alpha=0.6, label="UI Component Bounds")
    
    ax2_twin = ax2.twinx()
    ax2_twin.plot(time_sec, old_progress, color="red", linestyle="--", linewidth=2, label="Old Coord-Based Dwell (%)", alpha=0.7)
    ax2_twin.plot(time_sec, new_progress, color="#34d399", linewidth=3, label="New UI-Aware Dwell (%)")
    
    ax2_twin.axhline(100, color="white", linestyle=":", alpha=0.3)
    
    # Mark the click
    click_idx = np.where(new_progress >= 100)[0][0]
    ax2_twin.scatter([time_sec[click_idx]], [100], color="#34d399", s=100, zorder=5)
    ax2_twin.annotate("UI Auto-Click Fires!", xy=(time_sec[click_idx], 100), xytext=(time_sec[click_idx]-1, 80),
                      arrowprops=dict(facecolor='white', arrowstyle="->"), color="white", fontweight="bold")
    
    ax2.set_title("Smart UI Component Tracking (Jitter Immune)", color="white", fontsize=14, pad=15)
    ax2.set_xlabel("Time (seconds)", color="silver")
    ax2.set_ylabel("Cursor Y Position (px)", color="silver")
    ax2_twin.set_ylabel("Click Progress (%)", color="silver")
    
    ax2.set_ylim(550, 350)
    ax2_twin.set_ylim(0, 110)
    
    ax2.set_facecolor("#13233c")
    ax2.tick_params(colors="silver")
    ax2_twin.tick_params(colors="silver")
    
    lines, labels = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2_twin.legend(lines + lines2, labels + labels2, loc="lower right", facecolor="#0f172a", edgecolor="#334155", labelcolor="white")

    fig.patch.set_facecolor('#0f172a')
    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches='tight')
    print(f"Generated {out_path}")

if __name__ == "__main__":
    plot_v4_updates()
