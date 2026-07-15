"""Colored ring that follows the REAL cursor — the "is it on?" indicator.

Runs as its own little process (spawned by main.py). A transparent,
click-through, always-on-top window draws a ring around the cursor:

  green ring          = pointing (control active)
  red ring, bigger    = clicking / dragging
  orange ring         = paused (open palm)
  dim gray ring       = no hand found

It reads the current state from the .state file main.py writes, and the
cursor position straight from the OS, 60x a second.
"""

import objc  # noqa: F401  (pyobjc core, pulled in by pyautogui install)
from AppKit import (NSApplication, NSWindow, NSColor, NSBezierPath,
                    NSView, NSTimer, NSApp, NSBackingStoreBuffered,
                    NSWindowStyleMaskBorderless, NSScreen)
from Quartz import CGEventCreate, CGEventGetLocation
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), ".state")
SIZE = 120  # overlay window is a small square centred on the cursor

STYLES = {
    "P": (NSColor.systemGreenColor(), 22, 3.5),   # pointing
    "C": (NSColor.systemRedColor(), 34, 5.0),     # click / drag
    "S": (NSColor.systemOrangeColor(), 22, 3.5),  # paused
    "N": (NSColor.grayColor(), 14, 2.0),          # no hand
}


class RingView(NSView):
    state = "N"

    def drawRect_(self, rect):
        color, radius, width = STYLES.get(self.state, STYLES["N"])
        color.setStroke()
        c = SIZE / 2.0
        path = NSBezierPath.bezierPathWithOvalInRect_(
            ((c - radius, c - radius), (radius * 2, radius * 2)))
        path.setLineWidth_(width)
        path.stroke()


class Overlay:
    def __init__(self):
        self.win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            ((0, 0), (SIZE, SIZE)),
            NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
        self.win.setOpaque_(False)
        self.win.setBackgroundColor_(NSColor.clearColor())
        self.win.setIgnoresMouseEvents_(True)   # clicks pass through
        self.win.setLevel_(2**31 - 1)           # above everything
        self.win.setCollectionBehavior_(1 << 0 | 1 << 4)  # all spaces
        self.view = RingView.alloc().initWithFrame_(((0, 0), (SIZE, SIZE)))
        self.win.setContentView_(self.view)
        self.win.orderFrontRegardless()
        # main display height, to convert between coordinate systems
        self.screen_h = NSScreen.screens()[0].frame().size.height

    def tick_(self, timer):
        # follow the real cursor (Quartz y is top-down, AppKit bottom-up)
        loc = CGEventGetLocation(CGEventCreate(None))
        self.win.setFrameOrigin_((loc.x - SIZE / 2,
                                  self.screen_h - loc.y - SIZE / 2))
        try:
            with open(STATE_FILE) as f:
                state = f.read(1) or "N"
        except OSError:
            state = "N"
        if state == "Q":            # main app says quit
            NSApp.terminate_(None)
        if state != self.view.state:
            self.view.state = state
            self.view.setNeedsDisplay_(True)


def main():
    app = NSApplication.sharedApplication()
    overlay = Overlay()
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        1 / 30.0, overlay, "tick:", None, True)
    app.run()


if __name__ == "__main__":
    main()
