"""
Gestures Package - AI Gesture Mouse
Provides gesture recognition, tracking engine, neural network training, and fast mouse control.
"""

from .mouse_controller import FastMouseController
from .gesture_engine import GestureEngine, CameraStream

__all__ = ["FastMouseController", "GestureEngine", "CameraStream"]
