import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

# Current timestamp
now_dt = datetime.now()
current_timestamp = now_dt.strftime("%Y-%m-%d %H:%M:%S")

dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
history_path = os.path.join(dataset_dir, "training_history.npy")

if not os.path.exists(history_path):
    print(f"Error: {history_path} not found. Please train the model first.")
    exit(1)

print(f"Loading REAL training history from {history_path}...")
history_dict = np.load(history_path, allow_pickle=True).item()

# Extract real metrics
train_acc = history_dict.get('accuracy', [])
val_acc = history_dict.get('val_accuracy', [])
train_loss = history_dict.get('loss', [])
val_loss = history_dict.get('val_loss', [])

epochs_count = len(train_acc)
epochs = np.arange(1, epochs_count + 1)

# Exponential Smoothing for the "smooth" line (matches the previous style)
smooth_train_acc = np.zeros(epochs_count)
smooth_val_acc = np.zeros(epochs_count)
smooth_train_loss = np.zeros(epochs_count)
smooth_val_loss = np.zeros(epochs_count)

smooth_train_acc[0], smooth_val_acc[0] = train_acc[0], val_acc[0]
smooth_train_loss[0], smooth_val_loss[0] = train_loss[0], val_loss[0]

for i in range(1, epochs_count):
    smooth_train_acc[i] = smooth_train_acc[i-1] * 0.82 + train_acc[i] * 0.18
    smooth_val_acc[i] = smooth_val_acc[i-1] * 0.82 + val_acc[i] * 0.18
    smooth_train_loss[i] = smooth_train_loss[i-1] * 0.82 + train_loss[i] * 0.18
    smooth_val_loss[i] = smooth_val_loss[i-1] * 0.82 + val_loss[i] * 0.18

# --- OUTPUT DIRECTORY ---
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "plots")
os.makedirs(output_dir, exist_ok=True)

paper_path = os.path.join(output_dir, "paper_accuracy_loss_section.png")
accuracy_path = os.path.join(output_dir, "accuracy_graph.png")
loss_path = os.path.join(output_dir, "loss_graph.png")

final_tr_acc = smooth_train_acc[-1] * 100
final_va_acc = smooth_val_acc[-1] * 100
final_tr_loss = smooth_train_loss[-1]
final_va_loss = smooth_val_loss[-1]

# --- GENERATE COMBINED ACADEMIC PAPER GRAPH ---
fig = plt.figure(figsize=(8.5, 11), dpi=300)
fig.patch.set_facecolor('#ffffff')

# Header Titles
fig.text(0.5, 0.95, "Fig. 4.  AI Gesture Recognition Model Parameter Evaluation", ha='center', fontsize=11, fontfamily='serif')
fig.text(0.5, 0.91, "VIII.   ACCURACY & LOSS GRAPH", ha='center', fontsize=13, fontweight='bold',
         fontfamily='serif', bbox=dict(boxstyle='square,pad=0.35', facecolor='#dcfce7', edgecolor='none'))

# Timestamp in Header Sub-banner
fig.text(0.5, 0.88, f"Plotted Date & Time: {current_timestamp}  (REAL ML TRAINING DATA)", ha='center', fontsize=9.5, fontweight='bold',
         color='#1e293b', fontfamily='sans-serif')

# Subplot 1: Categorical Accuracy Graph
ax1 = fig.add_axes([0.1, 0.54, 0.8, 0.31])
ax1.grid(True, color='#e2e8f0', linestyle='-', linewidth=0.8)
ax1.set_axisbelow(True)

ax1.text(0.02, 0.93, f"epoch_categorical_accuracy (AI Gesture Model)\ntag: epoch_categorical_accuracy | Plotted: {current_timestamp}", 
         transform=ax1.transAxes, fontsize=8.5, color='#1e293b', fontfamily='sans-serif', verticalalignment='top')

# Plot Train & Val Accuracy
ax1.plot(epochs, train_acc, color='#93c5fd', alpha=0.35, linewidth=0.7, label='Train (Raw)')
ax1.plot(epochs, smooth_train_acc, color='#2563eb', linewidth=1.5, label=f'Train Accuracy (Final: {final_tr_acc:.1f}%)')

ax1.plot(epochs, val_acc, color='#fca5a5', alpha=0.35, linewidth=0.7, label='Val (Raw)')
ax1.plot(epochs, smooth_val_acc, color='#dc2626', linewidth=1.5, label=f'Validation Accuracy (Final: {final_va_acc:.1f}%)')

ax1.plot(epochs[-1], smooth_val_acc[-1], marker='o', markersize=5, color='#dc2626')

ax1.set_xlim(0, epochs_count)
ax1.set_ylim(max(0, min(train_acc) - 0.1), 1.05)
ax1.set_xticks(np.arange(0, epochs_count + 1, max(1, epochs_count // 6)))
ax1.tick_params(colors='#64748b', labelsize=8)
ax1.legend(loc='lower right', fontsize=8, frameon=True, facecolor='#ffffff', edgecolor='#cbd5e1')
for spine in ax1.spines.values():
    spine.set_color('#cbd5e1')

fig.text(0.5, 0.50, f"Fig. 5.  AI Gesture Recognition Accuracy Graph ({epochs_count} Epochs)", ha='center', fontsize=10.5, fontfamily='serif')

# Subplot 2: Categorical Loss Graph
ax2 = fig.add_axes([0.1, 0.12, 0.8, 0.31])
ax2.grid(True, color='#e2e8f0', linestyle='-', linewidth=0.8)
ax2.set_axisbelow(True)

ax2.text(0.02, 0.93, f"epoch_loss (AI Gesture Model)\ntag: epoch_loss | Plotted: {current_timestamp}", 
         transform=ax2.transAxes, fontsize=8.5, color='#1e293b', fontfamily='sans-serif', verticalalignment='top')

# Plot Train & Val Loss
ax2.plot(epochs, train_loss, color='#93c5fd', alpha=0.35, linewidth=0.7)
ax2.plot(epochs, smooth_train_loss, color='#2563eb', linewidth=1.5, label=f'Train Loss (Final: {final_tr_loss:.3f})')

ax2.plot(epochs, val_loss, color='#fca5a5', alpha=0.35, linewidth=0.7)
ax2.plot(epochs, smooth_val_loss, color='#dc2626', linewidth=1.5, label=f'Validation Loss (Final: {final_va_loss:.3f})')

ax2.plot(epochs[-1], smooth_val_loss[-1], marker='o', markersize=5, color='#dc2626')

ax2.set_xlim(0, epochs_count)
max_loss = max(max(train_loss), max(val_loss))
ax2.set_ylim(-0.05, max_loss * 1.1)
ax2.set_xticks(np.arange(0, epochs_count + 1, max(1, epochs_count // 6)))
ax2.tick_params(colors='#64748b', labelsize=8)
ax2.legend(loc='upper right', fontsize=8, frameon=True, facecolor='#ffffff', edgecolor='#cbd5e1')
for spine in ax2.spines.values():
    spine.set_color('#cbd5e1')

fig.text(0.5, 0.07, f"Fig. 6.  AI Gesture Recognition Categorical Loss Graph ({epochs_count} Epochs)", ha='center', fontsize=10.5, fontfamily='serif')
fig.text(0.5, 0.03, f"Generated & Plotted on: {current_timestamp} | AI Gesture Mouse", ha='center', fontsize=8.5, color='#64748b', fontfamily='sans-serif')

plt.savefig(paper_path, bbox_inches='tight', dpi=300)
plt.close()

# Save Individual Accuracy Graph
fig_acc, ax_acc = plt.subplots(figsize=(8, 4.5), dpi=300)
ax_acc.grid(True, color='#e2e8f0', linestyle='-', linewidth=0.8)
ax_acc.text(0.02, 0.93, f"epoch_categorical_accuracy | Plotted: {current_timestamp}\ntag: epoch_categorical_accuracy", transform=ax_acc.transAxes, fontsize=9, color='#1e293b')
ax_acc.plot(epochs, train_acc, color='#93c5fd', alpha=0.35, linewidth=0.7)
ax_acc.plot(epochs, smooth_train_acc, color='#2563eb', linewidth=1.6, label=f'Train Accuracy (Final: {final_tr_acc:.1f}%)')
ax_acc.plot(epochs, val_acc, color='#fca5a5', alpha=0.35, linewidth=0.7)
ax_acc.plot(epochs, smooth_val_acc, color='#dc2626', linewidth=1.6, label=f'Validation Accuracy (Final: {final_va_acc:.1f}%)')
ax_acc.set_xlim(0, epochs_count)
ax_acc.set_ylim(max(0, min(train_acc) - 0.1), 1.05)
ax_acc.set_xticks(np.arange(0, epochs_count + 1, max(1, epochs_count // 6)))
ax_acc.legend(loc='lower right', fontsize=8.5)
plt.tight_layout()
plt.savefig(accuracy_path, bbox_inches='tight', dpi=300)
plt.close()

# Save Individual Loss Graph
fig_loss, ax_loss = plt.subplots(figsize=(8, 4.5), dpi=300)
ax_loss.grid(True, color='#e2e8f0', linestyle='-', linewidth=0.8)
ax_loss.text(0.02, 0.93, f"epoch_loss | Plotted: {current_timestamp}\ntag: epoch_loss", transform=ax_loss.transAxes, fontsize=9, color='#1e293b')
ax_loss.plot(epochs, train_loss, color='#93c5fd', alpha=0.35, linewidth=0.7)
ax_loss.plot(epochs, smooth_train_loss, color='#2563eb', linewidth=1.6, label=f'Train Loss (Final: {final_tr_loss:.3f})')
ax_loss.plot(epochs, val_loss, color='#fca5a5', alpha=0.35, linewidth=0.7)
ax_loss.plot(epochs, smooth_val_loss, color='#dc2626', linewidth=1.6, label=f'Validation Loss (Final: {final_va_loss:.3f})')
ax_loss.set_xlim(0, epochs_count)
ax_loss.set_ylim(-0.05, max_loss * 1.1)
ax_loss.set_xticks(np.arange(0, epochs_count + 1, max(1, epochs_count // 6)))
ax_loss.legend(loc='upper right', fontsize=8.5)
plt.tight_layout()
plt.savefig(loss_path, bbox_inches='tight', dpi=300)
plt.close()

print(f"Successfully generated REAL ML accuracy & loss graphs from training_history.npy! | Time: {current_timestamp}")
