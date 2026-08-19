import cv2
import numpy as np
import mediapipe as mp
import os

print("Loading dataset templates for Live Testing...")
dataset_dir = "dataset"
X = np.load(os.path.join(dataset_dir, "X_gestures.npy"))
y = np.load(os.path.join(dataset_dir, "y_gestures.npy"))

# Define your 9 gestures in order
GESTURES = [
    "Move Cursor", "Drag & Drop", "Left Click", 
    "Right Click", "Double Click", "Scroll", 
    "Zoom", "Close Window", "Idle Fist"
]

# Compute the "Original Given Gesture" templates (the mathematical average of each class)
templates = []
for i in range(9):
    class_samples = X[y == i]
    if len(class_samples) > 0:
        templates.append(np.mean(class_samples, axis=0))
    else:
        templates.append(np.zeros(63))

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

# Open the webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Colors for the real-time graph
BAR_COLOR = (255, 130, 50)  # BGR (Blueish)
BAR_COLOR_MAX = (0, 220, 0) # Green for the highest match

print("\nWebcam successfully opened!")
print("Look at the right side of the window for the Real-Time Graphical Chart.")
print("Press 'q' in the camera window to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
        
    # Flip frame for mirror effect
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Extract hand tracking data
    results = hands.process(rgb_frame)
    
    # Create the dark Graphical Chart panel on the right (Width: 420px)
    graph_panel = np.zeros((480, 420, 3), dtype=np.uint8)
    
    # Title Text
    cv2.putText(graph_panel, "LIVE GESTURE MATCH RESULTS", (20, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(graph_panel, "Compares live hand to original dataset", (20, 55), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    
    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        
        # Extract features relative to the wrist (same as we did for original dataset)
        wrist = hand_landmarks.landmark[0]
        features = []
        for lm in hand_landmarks.landmark:
            features.extend([lm.x - wrist.x, lm.y - wrist.y, lm.z - wrist.z])
            
        live_features = np.array(features, dtype=np.float32)
        
        # Calculate real-time similarity to all 9 original templates
        similarities = []
        for template in templates:
            # Calculate 3D Euclidean distance between live hand and template hand
            dist = np.linalg.norm(template - live_features)
            
            # Convert distance to a 0-100% Match Score
            sim = np.exp(-dist * 4.5) * 100
            sim = max(0, min(100, sim))
            similarities.append(sim)
            
        max_idx = np.argmax(similarities)
        
        # Draw the real-time Bar Chart
        for i, (gest_name, sim) in enumerate(zip(GESTURES, similarities)):
            y_pos = 100 + i * 40
            
            # Gesture Label
            cv2.putText(graph_panel, gest_name, (20, y_pos + 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                        
            # Draw the visual bar
            bar_w = int((sim / 100.0) * 200) # Max 200 pixels wide
            color = BAR_COLOR_MAX if i == max_idx and sim > 40 else BAR_COLOR
            
            # Background bar (dark grey)
            cv2.rectangle(graph_panel, (150, y_pos), (150 + 200, y_pos + 20), (50, 50, 50), -1)
            # Foreground bar (dynamic color)
            if bar_w > 0:
                cv2.rectangle(graph_panel, (150, y_pos), (150 + bar_w, y_pos + 20), color, -1)
                
            # Percentage Number
            cv2.putText(graph_panel, f"{int(sim)}%", (360, y_pos + 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    else:
        cv2.putText(graph_panel, "No hand detected. Please show your hand.", (20, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

    # Combine the webcam feed (left) and the graph panel (right) into one window
    combined_frame = np.hstack((frame, graph_panel))
    
    cv2.imshow("Real-Time Gesture Graph Comparison", combined_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
        
cap.release()
cv2.destroyAllWindows()
