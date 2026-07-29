import ctypes
import time
import pyautogui

# Disable PyAutoGUI pause delay for zero-latency execution
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# Win32 API constants for direct input
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800

class FastMouseController:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.screen_w = self.user32.GetSystemMetrics(0)
        self.screen_h = self.user32.GetSystemMetrics(1)
        
        # Gesture states
        self.is_dragging = False
        self.last_click_time = 0
        self.click_cooldown = 0.25  # seconds debounce between clicks
        self.last_scroll_time = 0
        self.scroll_cooldown = 0.05
        self.last_zoom_time = 0
        self.zoom_cooldown = 0.25  # smooth debounce between zoom steps
        
    def move_to(self, x, y):
        """Ultra-fast Win32 cursor positioning (<1ms)"""
        target_x = max(0, min(self.screen_w - 1, int(x)))
        target_y = max(0, min(self.screen_h - 1, int(y)))
        self.user32.SetCursorPos(target_x, target_y)

    def left_click(self):
        """Single left click with debounce"""
        now = time.time()
        if now - self.last_click_time > self.click_cooldown:
            self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.last_click_time = now
            return True
        return False

    def right_click(self):
        """Single right click with debounce"""
        now = time.time()
        if now - self.last_click_time > self.click_cooldown:
            self.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            self.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            self.last_click_time = now
            return True
        return False

    def start_drag(self):
        """Begin drag (hold left mouse button)"""
        if not self.is_dragging:
            self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self.is_dragging = True

    def stop_drag(self):
        """End drag (release left mouse button)"""
        if self.is_dragging:
            self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.is_dragging = False

    def scroll(self, amount):
        """Scroll wheel (positive = up, negative = down)"""
        now = time.time()
        if now - self.last_scroll_time > self.scroll_cooldown:
            clicks = int(amount * 120)
            self.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, clicks, 0)
            self.last_scroll_time = now

    def zoom_in(self):
        """Triggers Zoom In (Ctrl + Plus) for active window"""
        now = time.time()
        if now - self.last_zoom_time > self.zoom_cooldown:
            pyautogui.hotkey('ctrl', '=')
            self.last_zoom_time = now
            return True
        return False

    def zoom_out(self):
        """Triggers Zoom Out (Ctrl + Minus) for active window"""
        now = time.time()
        if now - self.last_zoom_time > self.zoom_cooldown:
            pyautogui.hotkey('ctrl', '-')
            self.last_zoom_time = now
            return True
        return False
