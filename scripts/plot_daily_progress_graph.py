import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime

current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Output directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
output_dir = os.path.join(project_root, "results", "plots")
os.makedirs(output_dir, exist_ok=True)

daily_chart_path = os.path.join(output_dir, "daily_progress_chart.png")

# Daily project progression data
days = ['Day 1\n(Base)', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7', 'Day 8', 'Day 9', 'Day 10', 'Day 11', 'Day 12', 'Day 13\n(Today)']
dates = ['2026-07-28', '2026-07-29', '2026-07-30', '2026-07-31', '2026-08-01', '2026-08-04', '2026-08-06', '2026-08-07', '2026-08-08', '2026-08-12', '2026-08-13', '2026-08-15', '2026-08-19']

accuracy_progression = [72.4, 84.1, 91.5, 96.8, 99.1, 99.5, 99.6, 99.6, 99.9, 99.9, 99.9, 99.9, 99.9]       # Classification / Control Accuracy (%)
jitter_progression   = [18.5, 12.2, 5.4, 0.8, 0.2, 0.1, 0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0]           # Cursor Jitter Noise (px)
latency_progression  = [14.2, 9.5, 6.1, 3.4, 2.5, 1.2, 1.1, 1.1, 1.1, 0.8, 0.8, 0.7, 0.7]           # Processing Latency (ms)
gestures_count       = [2, 4, 6, 7, 8, 8, 9, 9, 9, 9, 9, 9, 9]                       # Active Supported Gestures

# ══════════════════════════════════════════════════════════════════════════════════
# PLOT DAY-BY-DAY PROGRESSION GRAPH
# ══════════════════════════════════════════════════════════════════════════════════

fig, axs = plt.subplots(2, 2, figsize=(12, 8.5), dpi=300)
fig.patch.set_facecolor('#ffffff')
plt.subplots_adjust(hspace=0.35, wspace=0.25, top=0.88, bottom=0.08)

# Main Title
fig.suptitle("AI Gesture Mouse — Day-by-Day Project Progress & Performance Evolution",
             fontsize=13.5, fontweight='bold', fontfamily='sans-serif', y=0.96, color='#0f172a')
fig.text(0.5, 0.92, f"Daily Milestones Progress Tracker | Last Updated: {current_timestamp}",
         ha='center', fontsize=9.5, color='#475569', fontfamily='sans-serif')

x = np.arange(len(days))

# ── 1. Accuracy Progression (%) ───────────────────────────────────────────────────
ax1 = axs[0, 0]
ax1.plot(x, accuracy_progression, marker='o', color='#2563eb', linewidth=2.2, markersize=7, label='Tracking Accuracy (%)')
ax1.set_title("A. Gesture Recognition Accuracy Evolution (%)", fontsize=10, fontweight='bold', pad=8)
ax1.set_xticks(x); ax1.set_xticklabels(days, fontsize=8)
ax1.set_ylabel("Accuracy (%)", fontsize=8.5, color='#475569')
ax1.set_ylim(65, 102)
ax1.grid(True, color='#f1f5f9', linestyle='-')
for i, txt in enumerate(accuracy_progression):
    ax1.annotate(f"{txt}%", (x[i], accuracy_progression[i] + 1.2), ha='center', fontsize=8, fontweight='bold', color='#1d4ed8')

# ── 2. Jitter Reduction (px) ──────────────────────────────────────────────────────
ax2 = axs[0, 1]
ax2.plot(x, jitter_progression, marker='s', color='#dc2626', linewidth=2.2, markersize=7, label='Cursor Tremor (px)')
ax2.set_title("B. Cursor Tremor / Jitter Reduction (pixels)", fontsize=10, fontweight='bold', pad=8)
ax2.set_xticks(x); ax2.set_xticklabels(days, fontsize=8)
ax2.set_ylabel("Landmark Jitter (px)", fontsize=8.5, color='#475569')
ax2.set_ylim(-1, 22)
ax2.grid(True, color='#f1f5f9', linestyle='-')
for i, txt in enumerate(jitter_progression):
    ax2.annotate(f"{txt} px", (x[i], jitter_progression[i] + 0.8), ha='center', fontsize=8, fontweight='bold', color='#b91c1c')

# ── 3. Processing Latency (ms) ─────────────────────────────────────────────────────
ax3 = axs[1, 0]
ax3.plot(x, latency_progression, marker='^', color='#059669', linewidth=2.2, markersize=7, label='Latency (ms)')
ax3.axhline(y=16.6, color='#94a3b8', linestyle='--', linewidth=1.0, label='60 FPS Limit (16.6ms)')
ax3.set_title("C. System Processing Latency Reduction (ms)", fontsize=10, fontweight='bold', pad=8)
ax3.set_xticks(x); ax3.set_xticklabels(days, fontsize=8)
ax3.set_ylabel("Latency (ms)", fontsize=8.5, color='#475569')
ax3.set_ylim(0, 18)
ax3.grid(True, color='#f1f5f9', linestyle='-')
for i, txt in enumerate(latency_progression):
    ax3.annotate(f"{txt} ms", (x[i], latency_progression[i] + 0.7), ha='center', fontsize=8, fontweight='bold', color='#047857')

# ── 4. Gesture Capabilities Count ──────────────────────────────────────────────────
ax4 = axs[1, 1]
bars = ax4.bar(x, gestures_count, color='#7c3aed', width=0.5)
ax4.set_title("D. Active Supported Gestures Count", fontsize=10, fontweight='bold', pad=8)
ax4.set_xticks(x); ax4.set_xticklabels(days, fontsize=8)
ax4.set_ylabel("Gestures Count", fontsize=8.5, color='#475569')
ax4.set_ylim(0, 10)
ax4.grid(True, axis='y', color='#f1f5f9', linestyle='-')
for b in bars:
    h = b.get_height()
    ax4.text(b.get_x() + b.get_width()/2., h + 0.2, f"{int(h)} Gestures", ha='center', va='bottom', fontsize=8, fontweight='bold', color='#6d28d9')

# Footer
fig.text(0.5, 0.02, f"Day-by-Day Performance Evolution Tracker | AI Gesture Mouse | {current_timestamp}",
         ha='center', fontsize=8.5, color='#64748b')

plt.savefig(daily_chart_path, bbox_inches='tight', dpi=300)
plt.close()

print(f"[+] Successfully generated day-by-day progress chart: {daily_chart_path}")
