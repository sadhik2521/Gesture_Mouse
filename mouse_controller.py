import ctypes
import ctypes.wintypes
import time

# ─────────────────────────────────────────────────────────────────────────────
# Win32 SendInput structures  (kernel-level, works on UAC-elevated apps & taskbar)
# ─────────────────────────────────────────────────────────────────────────────
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_WHEEL       = 0x0800
MOUSEEVENTF_ABSOLUTE    = 0x8000  # coordinates are 0-65535 (normalized)
MOUSEEVENTF_VIRTUALDESK = 0x4000  # map to virtual desktop (multi-monitor safe)

INPUT_MOUSE    = 0
WHEEL_DELTA    = 120


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("_",    _INPUT_UNION),
    ]


class FastMouseController:
    """
    Ultra-precise mouse controller using Win32 SendInput API.
    - Moves & clicks use MOUSEEVENTF_ABSOLUTE + MOUSEEVENTF_VIRTUALDESK for
      pixel-perfect targeting across the ENTIRE screen including taskbar.
    - Independent cooldowns for left-click, right-click, and scroll.
    - Supports left-click, right-click, double-click, drag, and scroll.
    """

    def __init__(self):
        self.user32   = ctypes.windll.user32
        self.screen_w = self.user32.GetSystemMetrics(0)   # SM_CXSCREEN
        self.screen_h = self.user32.GetSystemMetrics(1)   # SM_CYSCREEN

        # Virtual desktop dimensions (for multi-monitor absolute mapping)
        self.vdesk_w  = self.user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        self.vdesk_h  = self.user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        self.vdesk_x  = self.user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        self.vdesk_y  = self.user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN

        # State
        self.is_dragging      = False
        self._cur_x           = 0
        self._cur_y           = 0

        # Independent cooldowns (seconds)
        self.last_left_click   = 0.0
        self.left_cooldown     = 0.20   # 200 ms between left clicks

        self.last_right_click  = 0.0
        self.right_cooldown    = 0.35   # 350 ms between right clicks (context menu needs time)

        self.last_double_click = 0.0
        self.double_cooldown   = 0.50

        self.last_scroll_time  = 0.0
        self.scroll_cooldown   = 0.04   # ~25 scroll events/sec max

        self.last_zoom_time    = 0.0
        self.zoom_cooldown     = 0.30

    # ── Internal helpers ────────────────────────────────────────────────────

    def _pixel_to_abs(self, x, y):
        """
        Convert pixel coordinates to SendInput normalized 0-65535 range.
        Uses virtual desktop origin for multi-monitor correctness.
        """
        abs_x = int((x - self.vdesk_x) * 65535 / max(1, self.vdesk_w - 1))
        abs_y = int((y - self.vdesk_y) * 65535 / max(1, self.vdesk_h - 1))
        abs_x = max(0, min(65535, abs_x))
        abs_y = max(0, min(65535, abs_y))
        return abs_x, abs_y

    def _send_input(self, *inputs: INPUT):
        """Fire one or more INPUT events atomically via SendInput."""
        arr = (INPUT * len(inputs))(*inputs)
        self.user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

    def _build_mouse_input(self, flags, dx=0, dy=0, data=0) -> INPUT:
        mi = MOUSEINPUT(dx=dx, dy=dy, mouseData=data, dwFlags=flags,
                        time=0, dwExtraInfo=None)
        inp = INPUT(type=INPUT_MOUSE)
        inp._.mi = mi
        return inp

    def _move_input(self, x, y) -> INPUT:
        ax, ay = self._pixel_to_abs(x, y)
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        return self._build_mouse_input(flags, dx=ax, dy=ay)

    # ── Public API ──────────────────────────────────────────────────────────

    def move_to(self, x, y):
        """
        Pixel-perfect cursor move using SendInput ABSOLUTE coords.
        Replaces old SetCursorPos — now consistent with click coordinate space.
        """
        target_x = max(0, min(self.screen_w - 1, int(round(x))))
        target_y = max(0, min(self.screen_h - 1, int(round(y))))
        self._cur_x, self._cur_y = target_x, target_y
        self._send_input(self._move_input(target_x, target_y))

    def left_click(self):
        """Atomic move-to-position then left click (guarantees click lands correctly)."""
        now = time.perf_counter()
        if now - self.last_left_click < self.left_cooldown:
            return False
        # Atomic: move + down + up in one SendInput call
        self._send_input(
            self._move_input(self._cur_x, self._cur_y),
            self._build_mouse_input(MOUSEEVENTF_LEFTDOWN),
            self._build_mouse_input(MOUSEEVENTF_LEFTUP),
        )
        self.last_left_click = now
        return True

    def right_click(self):
        """Atomic move-to-position then right click."""
        now = time.perf_counter()
        if now - self.last_right_click < self.right_cooldown:
            return False
        self._send_input(
            self._move_input(self._cur_x, self._cur_y),
            self._build_mouse_input(MOUSEEVENTF_RIGHTDOWN),
            self._build_mouse_input(MOUSEEVENTF_RIGHTUP),
        )
        self.last_right_click = now
        return True

    def double_click(self):
        """Two rapid left clicks for opening files/apps."""
        now = time.perf_counter()
        if now - self.last_double_click < self.double_cooldown:
            return False
        self._send_input(
            self._move_input(self._cur_x, self._cur_y),
            self._build_mouse_input(MOUSEEVENTF_LEFTDOWN),
            self._build_mouse_input(MOUSEEVENTF_LEFTUP),
            self._build_mouse_input(MOUSEEVENTF_LEFTDOWN),
            self._build_mouse_input(MOUSEEVENTF_LEFTUP),
        )
        self.last_double_click = now
        self.last_left_click   = now  # prevent accidental single click after
        return True

    def start_drag(self):
        """Begin drag — hold left button down at current position."""
        if not self.is_dragging:
            self._send_input(
                self._move_input(self._cur_x, self._cur_y),
                self._build_mouse_input(MOUSEEVENTF_LEFTDOWN),
            )
            self.is_dragging = True

    def stop_drag(self):
        """Release drag — lift left button."""
        if self.is_dragging:
            self._send_input(self._build_mouse_input(MOUSEEVENTF_LEFTUP))
            self.is_dragging = False

    def scroll(self, amount):
        """
        Scroll wheel.  amount > 0 = scroll UP,  amount < 0 = scroll DOWN.
        amount is in wheel-click units (1.0 = one notch).
        """
        now = time.perf_counter()
        if now - self.last_scroll_time < self.scroll_cooldown:
            return
        clicks = int(amount * WHEEL_DELTA)
        if clicks == 0:
            return
        # mouseData for WHEEL uses a signed DWORD — cast via c_long
        self._send_input(
            self._build_mouse_input(MOUSEEVENTF_WHEEL, data=ctypes.c_ulong(clicks).value)
        )
        self.last_scroll_time = now

    def zoom_in(self):
        """Ctrl + = (browser/app zoom in)."""
        now = time.perf_counter()
        if now - self.last_zoom_time < self.zoom_cooldown:
            return False
        import pyautogui
        pyautogui.hotkey('ctrl', '=')
        self.last_zoom_time = now
        return True

    def zoom_out(self):
        """Ctrl + - (browser/app zoom out)."""
        now = time.perf_counter()
        if now - self.last_zoom_time < self.zoom_cooldown:
            return False
        import pyautogui
        pyautogui.hotkey('ctrl', '-')
        self.last_zoom_time = now
        return True

    def close_window(self):
        """Alt + F4 (Closes active window)."""
        now = time.perf_counter()
        if not hasattr(self, 'last_close_time'):
            self.last_close_time = 0.0
        if now - self.last_close_time < 1.2:
            return False
        import pyautogui
        pyautogui.hotkey('alt', 'f4')
        self.last_close_time = now
        return True
