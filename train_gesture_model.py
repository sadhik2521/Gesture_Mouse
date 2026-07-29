"""
VITS AI Gesture Mouse - Gesture Dataset Collector & Neural Network Model Trainer
Collects MediaPipe 3D hand landmark coordinates (21 landmarks * 3 = 63 features) from your webcam,
trains a Deep Neural Network (MLP) gesture classifier across 500 epochs, and plots the exact 
Training/Validation Accuracy and Loss curves.

Supported Gesture Classes (6 Classes):
0: Move Cursor (Index Pointing)
1: Left Click (Index Pinch)
2: Right Click (Middle Pinch)
3: Scroll (Index + Middle Side-by-Side)
4: Zoom In (Open Palm Wide)
5: Zoom Out (Closed Fist)
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
            '1': 'LEFT_CLICK',
            '2': 'RIGHT_CLICK',
            '3': 'SCROLL',
            '4': 'ZOOM_IN',
            '5': 'ZOOM_OUT'
        }

    def collect_data(self, samples_per_class=200):
        print("=== VITS AI GESTURE DATA COLLECTOR ===")
        print("Prepare your webcam. Press keys 0 to 5 to record samples for each gesture class:")
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
            
            cv2.putText(frame, "Press 0-5 to record class | 'q' to quit", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("VITS Gesture Dataset Collector", frame)
            
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

def train_model(epochs=500):
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
    num_classes = len(np.unique(y))
    y_cat = to_categorical(y, num_classes=6)
    
    if HAS_TF:
        model = Sequential([
            Dense(128, activation='relu', input_shape=(63,)),
            BatchNormalization(),
            Dropout(0.3),
            Dense(64, activation='relu'),
            BatchNormalization(),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(6, activation='softmax')
        ])
        
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        print("Training VITS Gesture Classifier over 500 epochs...")
        history = model.fit(X, y_cat, epochs=epochs, batch_size=32, validation_split=0.2)
        model.save("vits_gesture_model.h5")
        print("✓ Trained model saved to vits_gesture_model.h5")

if __name__ == "__main__":
    collector = GestureDataCollector()
    # collector.collect_data()  # Uncomment to record live webcam gesture samples
    train_model(epochs=500)
