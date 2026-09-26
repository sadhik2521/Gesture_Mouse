"""
AI Gesture Mouse - Gesture Dataset Collector & Neural Network Model Trainer
Collects MediaPipe 3D hand landmark coordinates (21 landmarks * 3 = 63 features) from your webcam,
trains a Deep Neural Network (MLP) gesture classifier across 100 epochs, and plots the exact 
Training/Validation Accuracy and Loss curves.

Supported Gesture Classes (9 Classes):
0: Move Cursor (Index Pointing)
1: Drag & Drop (Pinch)
2: Left Click (Peace Sign)
3: Right Click (L-Shape)
4: Double Click (Thumb Only)
5: Scroll (Open Palm)
6: Zoom (Rock Sign)
7: Close Window (Pinky Extended)
8: Idle (Closed Fist)
"""

import cv2
import mediapipe as mp
import numpy as np
import os
import time

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
    from tensorflow.keras.utils import to_categorical
    HAS_TF = True
except ImportError:
    HAS_TF = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset") if os.path.exists(os.path.join(PROJECT_ROOT, "dataset")) else "dataset"

class GestureDataCollector:
    def __init__(self, dataset_dir=None):
        self.dataset_dir = dataset_dir or DEFAULT_DATASET_DIR
        os.makedirs(self.dataset_dir, exist_ok=True)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils
        
        self.classes = {
            '0': 'MOVE_CURSOR',
            '1': 'DRAG_DROP',
            '2': 'LEFT_CLICK',
            '3': 'RIGHT_CLICK',
            '4': 'DOUBLE_CLICK',
            '5': 'SCROLL',
            '6': 'ZOOM',
            '7': 'CLOSE_WINDOW',
            '8': 'IDLE_FIST'
        }

    def collect_data(self, samples_per_class=200):
        print("=== AI GESTURE DATA COLLECTOR ===")
        print("Prepare your webcam. Press keys 0 to 8 to record samples for each gesture class:")
        for k, v in self.classes.items():
            print(f"  Key '{k}': {v}")
        print("  Press 'q' to finish collection.")
        
        cap = cv2.VideoCapture(0)
        
        data = []
        labels = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(rgb)
            
            curr_features = None
            if result.multi_hand_landmarks:
                hand_lms = result.multi_hand_landmarks[0]
                self.mp_draw.draw_landmarks(frame, hand_lms, self.mp_hands.HAND_CONNECTIONS)
                
                # Normalize landmarks relative to wrist (landmark 0)
                wrist = hand_lms.landmark[0]
                features = []
                for lm in hand_lms.landmark:
                    features.extend([lm.x - wrist.x, lm.y - wrist.y, lm.z - wrist.z])
                curr_features = features
            
            cv2.putText(frame, "Press 0-8 to record class | 'q' to quit", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("Gesture Dataset Collector", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif chr(key) in self.classes and curr_features is not None:
                class_id = int(chr(key))
                data.append(curr_features)
                labels.append(class_id)
                print(f"[+] Saved sample for Class {class_id}: {self.classes[chr(key)]} (Total: {len(labels)})")

        cap.release()
        cv2.destroyAllWindows()
        
        if len(data) > 0:
            np.save(os.path.join(self.dataset_dir, "X_gestures.npy"), np.array(data))
            np.save(os.path.join(self.dataset_dir, "y_gestures.npy"), np.array(labels))
            print(f"[OK] Saved dataset with {len(data)} samples to {self.dataset_dir}/")
            export_csv_from_numpy(self.dataset_dir)

    def replace_gesture(self, target_class_id: int):
        target_str = str(target_class_id)
        if target_str not in self.classes:
            print(f"Error: Invalid gesture ID {target_class_id}. Choose between 0 and 8.")
            return

        gname = self.classes[target_str]
        print(f"=== REPLACING GESTURE {target_class_id}: {gname} ===")

        x_path = os.path.join(self.dataset_dir, "X_gestures.npy")
        y_path = os.path.join(self.dataset_dir, "y_gestures.npy")

        if os.path.exists(x_path) and os.path.exists(y_path):
            X_existing = np.load(x_path)
            y_existing = np.load(y_path)
            # Filter out old samples of this specific gesture
            keep_mask = (y_existing != target_class_id)
            X_kept = X_existing[keep_mask]
            y_kept = y_existing[keep_mask]
            print(f"Retained {len(y_kept)} samples from other classes. Replacing class {target_class_id}...")
        else:
            X_kept = np.empty((0, 63))
            y_kept = np.empty((0,), dtype=int)

        print("Hold your hand in position.")
        print("Press SPACEBAR to capture samples (hold down to rapidly record ~200 samples).")
        print("Press 'q' when finished to save and update the dataset.")

        cap = cv2.VideoCapture(0)
        new_data = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(rgb)

            curr_features = None
            if result.multi_hand_landmarks:
                hand_lms = result.multi_hand_landmarks[0]
                self.mp_draw.draw_landmarks(frame, hand_lms, self.mp_hands.HAND_CONNECTIONS)
                wrist = hand_lms.landmark[0]
                curr_features = []
                for lm in hand_lms.landmark:
                    curr_features.extend([lm.x - wrist.x, lm.y - wrist.y, lm.z - wrist.z])

            cv2.putText(frame, f"Replacing Class {target_class_id}: {gname}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"Recorded: {len(new_data)} | Hold SPACE to record, 'q' to save", (20, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            cv2.imshow(f"Replace Gesture: {gname}", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' ') and curr_features is not None:
                new_data.append(curr_features)
                print(f"[+] Recorded sample #{len(new_data)} for {gname}")

        cap.release()
        cv2.destroyAllWindows()

        if len(new_data) > 0:
            X_new = np.array(new_data)
            y_new = np.full(len(new_data), target_class_id, dtype=int)

            if len(X_kept) > 0:
                X_final = np.vstack([X_kept, X_new])
                y_final = np.concatenate([y_kept, y_new])
            else:
                X_final = X_new
                y_final = y_new

            np.save(x_path, X_final)
            np.save(y_path, y_final)
            print(f"[OK] Successfully replaced Class {target_class_id} with {len(new_data)} new samples.")
            print(f"Total dataset size: {len(y_final)} samples.")
            export_csv_from_numpy(self.dataset_dir)
        else:
            print("No new samples were recorded. Dataset unchanged.")

def export_csv_from_numpy(dataset_dir=None):
    import pandas as pd
    dataset_dir = dataset_dir or DEFAULT_DATASET_DIR
    x_path = os.path.join(dataset_dir, "X_gestures.npy")
    y_path = os.path.join(dataset_dir, "y_gestures.npy")
    if not (os.path.exists(x_path) and os.path.exists(y_path)):
        return
    X = np.load(x_path)
    y = np.load(y_path)
    
    gesture_names = {
        0: 'Move Cursor (Index Pointing)',
        1: 'Drag & Drop (Pinch)',
        2: 'Left Click (Peace Sign)',
        3: 'Right Click (L-Shape)',
        4: 'Double Click (Thumb Only)',
        5: 'Scroll (Open Palm)',
        6: 'Zoom (Rock Sign)',
        7: 'Close Window (Pinky Extended)',
        8: 'Idle (Closed Fist)'
    }
    landmark_names = [
        'wrist',
        'thumb_cmc', 'thumb_mcp', 'thumb_ip', 'thumb_tip',
        'index_mcp', 'index_pip', 'index_dip', 'index_tip',
        'middle_mcp', 'middle_pip', 'middle_dip', 'middle_tip',
        'ring_mcp', 'ring_pip', 'ring_dip', 'ring_tip',
        'pinky_mcp', 'pinky_pip', 'pinky_dip', 'pinky_tip'
    ]
    col_names = ['gesture_id', 'gesture_name']
    for i, lm in enumerate(landmark_names):
        col_names.extend([f'lm{i}_{lm}_x', f'lm{i}_{lm}_y', f'lm{i}_{lm}_z'])
    
    rows = []
    for i in range(len(y)):
        gid = int(y[i])
        gname = gesture_names.get(gid, f'Gesture_{gid}')
        rows.append([gid, gname] + [round(val, 4) for val in X[i]])
    
    df = pd.DataFrame(rows, columns=col_names)
    csv_path = os.path.join(dataset_dir, "gestures_data.csv")
    df.to_csv(csv_path, index=False)
    print(f"[OK] Synchronized and saved {csv_path} ({len(df)} samples)")
    
    num_cols = [c for c in df.columns if c not in ['gesture_id', 'gesture_name']]
    avg_df = df.groupby(['gesture_id', 'gesture_name'])[num_cols].mean().round(4).reset_index()
    avg_df.to_csv(os.path.join(dataset_dir, "gesture_averages_reference.csv"), index=False)

def sync_from_csv(dataset_dir=None):
    import pandas as pd
    dataset_dir = dataset_dir or DEFAULT_DATASET_DIR
    csv_path = os.path.join(dataset_dir, "gestures_data.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return False
    df = pd.read_csv(csv_path)
    feature_cols = [c for c in df.columns if c.startswith('lm')]
    if len(feature_cols) != 63:
        feature_cols = [c for c in df.columns if c not in ['gesture_id', 'gesture_name']]
    
    X = df[feature_cols].to_numpy(dtype=np.float32)
    y = df['gesture_id'].to_numpy(dtype=np.int32)
    
    np.save(os.path.join(dataset_dir, "X_gestures.npy"), X)
    np.save(os.path.join(dataset_dir, "y_gestures.npy"), y)
    print(f"[OK] Loaded {len(df)} samples from {csv_path} and updated X_gestures.npy & y_gestures.npy")
    return True

def train_model(epochs=100, dataset_dir=None):
    dataset_dir = dataset_dir or DEFAULT_DATASET_DIR
    x_path = os.path.join(dataset_dir, "X_gestures.npy")
    y_path = os.path.join(dataset_dir, "y_gestures.npy")
    
    if not (os.path.exists(x_path) and os.path.exists(y_path)):
        print(f"Dataset not found in {dataset_dir}/.")
        return

    X = np.load(x_path)
    y = np.load(y_path)
    
    print(f"Loaded dataset: X shape {X.shape}, y shape {y.shape}")
    
    # Correctly and reproducibly shuffle the dataset before splitting
    # This ensures the 20% validation split contains all 9 gesture classes
    rng = np.random.RandomState(42)
    indices = np.arange(X.shape[0])
    rng.shuffle(indices)
    X = X[indices]
    y = y[indices]
    
    num_classes = len(np.unique(y))
    y_cat = to_categorical(y, num_classes=9)
    
    if HAS_TF:
        model = Sequential([
            Dense(128, activation='relu', input_shape=(63,)),
            BatchNormalization(),
            Dropout(0.3),
            Dense(64, activation='relu'),
            BatchNormalization(),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(9, activation='softmax')
        ])
        
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        print(f"Training Gesture Classifier over {epochs} epochs...")
        history = model.fit(X, y_cat, epochs=epochs, batch_size=32, validation_split=0.2)
        model_save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gesture_model.h5")
        model.save(model_save_path)
        
        # Save the real training history for plot_accuracy_loss.py to use
        np.save(os.path.join(dataset_dir, "training_history.npy"), history.history)
        print(f"[OK] Trained model saved to {model_save_path}")
        print(f"[OK] Real training history saved to {dataset_dir}/training_history.npy")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI Gesture Mouse - Dataset and Model Tools")
    parser.add_argument("--collect", action="store_true", help="Launch webcam collector to record new gesture data")
    parser.add_argument("--replace-gesture", type=int, choices=range(0, 9), help="Replace samples of a specific gesture ID (0-8) using webcam")
    parser.add_argument("--from-csv", action="store_true", help="Sync dataset from edited gestures_data.csv into .npy")
    parser.add_argument("--train", action="store_true", help="Train model using the current dataset")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs (default: 100)")
    args = parser.parse_args()

    if args.collect:
        collector = GestureDataCollector()
        collector.collect_data()
    elif args.replace_gesture is not None:
        collector = GestureDataCollector()
        collector.replace_gesture(args.replace_gesture)
    elif args.from_csv:
        sync_from_csv()
    else:
        # Default behavior: train model
        train_model(epochs=args.epochs)
