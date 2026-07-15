"""Move the REAL Mac cursor via Quartz (native macOS API).

We talk to Core Graphics directly instead of pyautogui — pyautogui's
per-move overhead on macOS causes lag/hangs at camera framerates.

Click gotcha: macOS apps ignore mouseDown/Up events unless the
kCGMouseEventClickState field is set. We set it explicitly.
"""

import Quartz


def _post(event_type, x, y, click_state=0):
    ev = Quartz.CGEventCreateMouseEvent(
        None, event_type, (x, y), Quartz.kCGMouseButtonLeft)
    if click_state:
        Quartz.CGEventSetIntegerValueField(
            ev, Quartz.kCGMouseEventClickState, click_state)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


class MouseController:
    def __init__(self):
        bounds = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
        self.screen_w = int(bounds.size.width)
        self.screen_h = int(bounds.size.height)
        self._dragging = False
        self._click_state = 1
        self._x = self.screen_w // 2
        self._y = self.screen_h // 2

    @property
    def pos(self):
        return self._x, self._y

    def move(self, x, y):
        """Move the real cursor to absolute screen point (x, y)."""
        nx = max(0, min(self.screen_w - 1, int(x)))
        ny = max(0, min(self.screen_h - 1, int(y)))
        if nx == self._x and ny == self._y and not self._dragging:
            return                     # nothing changed: don't post an event
        self._x, self._y = nx, ny
        if self._dragging:
            _post(Quartz.kCGEventLeftMouseDragged, self._x, self._y,
                  click_state=self._click_state)
        else:
            _post(Quartz.kCGEventMouseMoved, self._x, self._y)

    def press(self, click_state=1):
        """Mouse button down. click_state=2 marks the second click of a
        double-click (macOS opens files/apps only when this is set)."""
        if not self._dragging:
            self._click_state = click_state
            _post(Quartz.kCGEventLeftMouseDown, self._x, self._y,
                  click_state=click_state)
            self._dragging = True

    def release(self):
        """Mouse button up at the current position."""
        if self._dragging:
            _post(Quartz.kCGEventLeftMouseUp, self._x, self._y,
                  click_state=self._click_state)
            self._dragging = False

    def double_click(self):
        """Full double-click at the current position (opens files/apps,
        and works as a plain click on buttons/links too)."""
        x, y = self._x, self._y
        _post(Quartz.kCGEventLeftMouseDown, x, y, click_state=1)
        _post(Quartz.kCGEventLeftMouseUp, x, y, click_state=1)
        _post(Quartz.kCGEventLeftMouseDown, x, y, click_state=2)
        _post(Quartz.kCGEventLeftMouseUp, x, y, click_state=2)

    @property
    def is_pressed(self):
        return self._dragging
