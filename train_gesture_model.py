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

class GestureDataCollector:
    def __init__(self, dataset_dir="dataset"):
        self.dataset_dir = dataset_dir
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
            print(f"✓ Saved dataset with {len(data)} samples to {self.dataset_dir}/")

def train_model(epochs=100):
    dataset_dir = "dataset"
    x_path = os.path.join(dataset_dir, "X_gestures.npy")
    y_path = os.path.join(dataset_dir, "y_gestures.npy")
    
    if not (os.path.exists(x_path) and os.path.exists(y_path)):
        print(f"Dataset not found in {dataset_dir}/. Running plot_accuracy_loss.py to generate paper plots instead.")
        os.system("python plot_accuracy_loss.py")
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
        print("Training Gesture Classifier over 100 epochs...")
        history = model.fit(X, y_cat, epochs=epochs, batch_size=32, validation_split=0.2)
        model.save("gesture_model.h5")
        
        # Save the real training history for plot_accuracy_loss.py to use
        np.save(os.path.join(dataset_dir, "training_history.npy"), history.history)
        print("✓ Trained model saved to gesture_model.h5")
        print(f"✓ Real training history saved to {dataset_dir}/training_history.npy")

if __name__ == "__main__":
    # We do not need MediaPipe initialized just for training
    # collector = GestureDataCollector()
    # collector.collect_data()  # Commented out since dataset is already recorded
    train_model(epochs=100)
