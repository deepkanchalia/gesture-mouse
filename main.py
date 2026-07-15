"""Hand-Gesture Mouse Control — v5 (hover-arm design, all-day light).

Move your hand              -> cursor follows (anchored to your knuckle)
Hold still on a target ~2s  -> ARMED (cursor locks on the target)
While armed:
  flick index+thumb 3 times -> OPEN it (double-click)
  close hand, hold ~2s      -> PICK UP | open hand -> DROP
Move your hand away         -> disarms, back to normal tracking
No hand in frame            -> cursor freezes
ESC or q (in the camera window) -> quit

The cursor is FROZEN on the target while armed, so taps can't drift
off the icon. Nothing is ever clicked without arming first.

Ring colors: green = tracking, orange = armed / holding,
red = carrying or click, gray = no hand.
"""

import os
import subprocess
import sys
import time

import cv2

from hand_tracker import HandTracker, MIDDLE_MCP
from smoothing import Vec2Filter
from mouse_control import MouseController

# --- Tuning knobs (safe to tweak) -----------------------------------------
# Active region: inner box of the CAMERA frame mapped to the whole screen.
ACTIVE_X0, ACTIVE_Y0 = 0.15, 0.15
ACTIVE_X1, ACTIVE_Y1 = 0.85, 0.85

# Pinch hysteresis (from Deep's logged hand).
PINCH_CLOSE = 0.35
PINCH_OPEN = 0.55

# ARM: hold the cursor inside this radius for this long to lock on.
ARM_HOLD_SEC = 2.0
DWELL_RADIUS_PX = 40
# Moving this far away while armed = disarm (generous: taps jiggle the hand).
DISARM_MOVE_PX = 150
# Armed but idle for this long = disarm.
ARMED_TIMEOUT_SEC = 6.0

# OPEN: this many pinch flicks while armed.
OPEN_TAPS = 3
TAPS_WINDOW_SEC = 4.0     # all taps must land within this of the first

# PICK: hand kept closed this long (while armed) picks the target up.
GRAB_HOLD_SEC = 2.0
# --------------------------------------------------------------------------

STATE_FILE = os.path.join(os.path.dirname(__file__), ".state")


def write_state(ch, _last=[""]):
    if ch == _last[0]:               # only touch the file on change
        return
    _last[0] = ch
    try:
        # write-then-rename so the overlay never reads a half-written file
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            f.write(ch)
        os.replace(tmp, STATE_FILE)
    except OSError:
        pass


def to_screen(nx, ny, mouse):
    fx = (nx - ACTIVE_X0) / (ACTIVE_X1 - ACTIVE_X0)
    fy = (ny - ACTIVE_Y0) / (ACTIVE_Y1 - ACTIVE_Y0)
    fx = max(0.0, min(1.0, fx))
    fy = max(0.0, min(1.0, fy))
    return fx * mouse.screen_w, fy * mouse.screen_h


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("\nERROR: could not open the camera.")
        print("Mac: System Settings > Privacy & Security > Camera -> enable, retry.\n")
        return
    # Low resolution on purpose: hand landmarks don't need more, and this
    # is what keeps the machine cool over a 15-hour day.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    tracker = HandTracker()
    smoother = Vec2Filter(freq=30.0, min_cutoff=1.2, beta=0.02)
    mouse = MouseController()

    write_state("N")
    overlay = subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), "overlay.py")])

    print(f"Camera ready. Screen {mouse.screen_w}x{mouse.screen_h}.", flush=True)
    print("hold still 2s = arm | 3 flicks = open | close hand 2s = pick, "
          "open = drop | ESC = quit", flush=True)

    # dwell / arm state
    armed = False
    dwell_x, dwell_y = 0.0, 0.0   # centre of the stillness test
    dwell_start = 0.0
    armed_at = 0.0
    # pinch state
    pinch_closed = False
    close_time = 0.0
    tap_times = []                # timestamps of flicks while armed
    # actions
    carrying = False
    click_flash_until = 0.0

    def disarm():
        nonlocal armed, tap_times, pinch_closed
        armed = False
        tap_times = []

    bad_frames = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                # Camera unplugged / hijacked: don't spin at 100% CPU forever.
                bad_frames += 1
                if bad_frames > 90:      # ~3s of nothing
                    print("\nERROR: lost the camera. If an iPhone appeared "
                          "instead of your webcam, turn off Continuity "
                          "Camera (see README) and re-run.")
                    break
                time.sleep(0.03)
                continue
            bad_frames = 0
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hand, mp_result = tracker.process(rgb)
            tracker.draw(frame, mp_result)
            h, w = frame.shape[:2]

            state, color, ring = "NO HAND (cursor frozen)", (0, 0, 255), "N"
            hud2 = ""

            if hand is not None:
                pinch_val = hand.pinch_distance
                now = time.time()

                nx, ny, _ = hand.landmarks[MIDDLE_MCP]
                sx, sy = to_screen(nx, ny, mouse)
                sx, sy = smoother(sx, sy)

                # --- pinch open/close edges ---
                closed_now = False
                opened_now = False
                if not pinch_closed and pinch_val < PINCH_CLOSE:
                    pinch_closed = True
                    close_time = now
                    closed_now = True
                elif pinch_closed and pinch_val > PINCH_OPEN:
                    pinch_closed = False
                    opened_now = True

                if carrying:
                    # dragging: cursor moves, open hand drops it
                    mouse.move(sx, sy)
                    if opened_now:
                        carrying = False
                        mouse.release()
                    state, color, ring = "CARRYING (open hand to drop)", (0, 150, 255), "C"

                elif armed:
                    # cursor stays LOCKED on the target
                    drift = max(abs(sx - dwell_x), abs(sy - dwell_y))
                    held = now - close_time if pinch_closed else 0.0

                    if opened_now:
                        tap_times.append(now)
                        tap_times = [t for t in tap_times
                                     if now - t < TAPS_WINDOW_SEC]
                        if len(tap_times) >= OPEN_TAPS:
                            mouse.double_click()        # OPEN!
                            click_flash_until = now + 0.6
                            disarm()
                            dwell_x, dwell_y = sx, sy
                            dwell_start = now
                    elif pinch_closed and held >= GRAB_HOLD_SEC:
                        carrying = True                 # PICK UP
                        mouse.press(1)
                        disarm()
                    elif drift > DISARM_MOVE_PX and not pinch_closed:
                        disarm()                        # walked away
                        dwell_x, dwell_y = sx, sy
                        dwell_start = now
                    elif (now - armed_at > ARMED_TIMEOUT_SEC
                            and not tap_times and not pinch_closed):
                        disarm()                        # nothing happened
                        dwell_x, dwell_y = sx, sy
                        dwell_start = now

                    if armed:
                        if pinch_closed and held > 0.4:
                            state = f"HOLDING {held:.1f}s / {GRAB_HOLD_SEC:.0f}s to pick"
                        elif tap_times:
                            state = f"FLICK {len(tap_times)}/{OPEN_TAPS} to open"
                        else:
                            state = "ARMED - 3 flicks = open, close 2s = pick"
                        color, ring = (0, 200, 255), "S"
                    elif time.time() < click_flash_until:
                        state, color, ring = "OPEN!", (0, 150, 255), "C"
                    else:
                        state, color, ring = "TRACKING", (0, 255, 0), "P"

                else:
                    # normal tracking + dwell detection
                    mouse.move(sx, sy)
                    if max(abs(sx - dwell_x), abs(sy - dwell_y)) > DWELL_RADIUS_PX:
                        dwell_x, dwell_y = sx, sy       # moved: restart dwell
                        dwell_start = now
                    elif now - dwell_start >= ARM_HOLD_SEC and not pinch_closed:
                        armed = True                    # locked on target
                        armed_at = now
                        tap_times = []
                        dwell_x, dwell_y = mouse.pos

                    if time.time() < click_flash_until:
                        state, color, ring = "OPEN!", (0, 150, 255), "C"
                    else:
                        still = now - dwell_start
                        if still > 0.6:
                            state = f"HOLD STILL {still:.1f}s / {ARM_HOLD_SEC:.0f}s to arm"
                            color, ring = (0, 255, 0), "P"
                        else:
                            state, color, ring = "TRACKING", (0, 255, 0), "P"

                hud2 = f"pinch {pinch_val:.2f}"
                cv2.circle(frame, (int(nx * w), int(ny * h)), 8,
                           (0, 255, 0), -1)
            else:
                if carrying:
                    mouse.release()
                    carrying = False
                disarm()
                pinch_closed = False
                dwell_start = 0.0

            write_state(ring)

            # HUD
            cv2.rectangle(frame,
                          (int(ACTIVE_X0 * w), int(ACTIVE_Y0 * h)),
                          (int(ACTIVE_X1 * w), int(ACTIVE_Y1 * h)),
                          (200, 200, 200), 1)
            cv2.putText(frame, state, (14, 32), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, color, 2)
            if hud2:
                cv2.putText(frame, hud2, (14, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            cv2.putText(frame,
                        "hold still 2s = arm | 3 flicks = open | close 2s = pick | ESC = quit",
                        (14, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (255, 255, 255), 1)
            cv2.imshow("Gesture Mouse (ESC to quit)", frame)

            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                break
    finally:
        mouse.release()
        write_state("Q")
        cap.release()
        cv2.destroyAllWindows()
        try:
            overlay.wait(timeout=2)
        except subprocess.TimeoutExpired:
            overlay.kill()


if __name__ == "__main__":
    main()
