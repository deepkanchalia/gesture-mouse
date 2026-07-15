"""Pinch debugger — mirrors main.py v6 double-pinch logic and logs WHY
each attempt succeeded or failed to pinch_log.txt.

Run it, do ~10 deliberate double-pinches at the camera, press ESC.
Then read pinch_log.txt: every event says what the app saw.
"""

import time

import cv2

from hand_tracker import HandTracker

# Same values as main.py — keep in sync.
PINCH_CLOSE = 0.35
PINCH_OPEN = 0.55
OPEN_TAPS = 2
TAPS_WINDOW_SEC = 2.5

LOG = open("pinch_log.txt", "w")


def log(msg):
    line = f"{time.time():.3f} {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    tracker = HandTracker()

    pinch_closed = False
    tap_times = []
    close_t = 0.0
    min_pinch = 99.0     # lowest value inside current close
    max_open = 0.0       # highest value since last close
    frames = 0
    hand_frames = 0
    t0 = time.time()
    opens = 0

    log(f"START thresholds close<{PINCH_CLOSE} open>{PINCH_OPEN} "
        f"taps={OPEN_TAPS} window={TAPS_WINDOW_SEC}s")

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frames += 1
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hand, mp_result = tracker.process(rgb)
        tracker.draw(frame, mp_result)
        now = time.time()

        state = "NO HAND"
        if hand is not None:
            hand_frames += 1
            v = hand.pinch_distance
            state = f"pinch {v:.2f}  taps {len(tap_times)}"

            if not pinch_closed and v < PINCH_CLOSE:
                pinch_closed = True
                close_t = now
                min_pinch = v
                log(f"CLOSE  val={v:.2f}  (max open since last: {max_open:.2f})")
                max_open = 0.0
            elif pinch_closed:
                min_pinch = min(min_pinch, v)
                if v > PINCH_OPEN:
                    pinch_closed = False
                    dur = now - close_t
                    expired = [t for t in tap_times
                               if now - t >= TAPS_WINDOW_SEC]
                    tap_times = [t for t in tap_times
                                 if now - t < TAPS_WINDOW_SEC]
                    if expired:
                        log(f"  WINDOW EXPIRED: previous tap was "
                            f"{now - expired[-1]:.2f}s ago (limit {TAPS_WINDOW_SEC}s)")
                    tap_times.append(now)
                    gap = (tap_times[-1] - tap_times[-2]
                           if len(tap_times) > 1 else 0.0)
                    log(f"TAP {len(tap_times)}  held={dur:.2f}s  "
                        f"min={min_pinch:.2f}  gap={gap:.2f}s")
                    if len(tap_times) >= OPEN_TAPS:
                        opens += 1
                        log(f">>> OPEN #{opens} (would double-click)")
                        tap_times = []
            else:
                max_open = max(max_open, v)
        else:
            if pinch_closed:
                log("HAND LOST mid-pinch (tracking dropout!)")
            pinch_closed = False

        cv2.putText(frame, state, (14, 32), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"OPENS: {opens}  (ESC = quit)", (14, 64),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
        cv2.imshow("Pinch Debug (ESC to quit)", frame)
        if cv2.waitKey(1) & 0xFF in (27, ord("q")):
            break

    dt = time.time() - t0
    log(f"END fps={frames / dt:.1f} hand_detected={hand_frames}/{frames} "
        f"frames opens={opens}")
    cap.release()
    cv2.destroyAllWindows()
    LOG.close()


if __name__ == "__main__":
    main()
