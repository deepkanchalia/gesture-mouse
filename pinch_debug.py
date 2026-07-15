"""Pinch diagnostic — NO mouse control.

Runs the SAME decision logic as main.py and logs every event to
pinch_log.txt so we can see why clicks fail. ESC/q to quit.
"""

import time

import cv2

from hand_tracker import HandTracker

# Same values as main.py
PINCH_CLOSE = 0.35
PINCH_OPEN = 0.55
DOUBLE_PINCH_WINDOW = 1.0
GRAB_MAX_FINGERS_UP = 1

LOG = open("pinch_log.txt", "w")


def log(msg):
    line = f"{time.time():.2f} {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("camera failed")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
    tracker = HandTracker()

    grabbing = False
    pinch_closed = False
    last_tap_time = 0.0
    last_sample = 0.0
    verdict = ""

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hand, mp_result = tracker.process(rgb)
        tracker.draw(frame, mp_result)
        h, w = frame.shape[:2]

        if hand is None:
            cv2.putText(frame, "NO HAND", (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4)
            grabbing = False
            pinch_closed = False
        else:
            p = hand.pinch_distance
            ups = hand.fingers_up()
            n_up = sum(ups)
            now = time.time()

            # --- exact main.py logic, but logging instead of clicking ---
            if (not grabbing and p < PINCH_CLOSE
                    and n_up <= GRAB_MAX_FINGERS_UP):
                grabbing = True
                pinch_closed = False
                last_tap_time = 0.0
                verdict = "GRAB (drag)"
                log(f"GRAB start  pinch={p:.2f} n_up={n_up} fingers={ups}")
            elif grabbing and p > PINCH_OPEN:
                grabbing = False
                verdict = ""
                log(f"GRAB end    pinch={p:.2f} n_up={n_up}")

            if not grabbing:
                if (not pinch_closed and p < PINCH_CLOSE
                        and n_up > GRAB_MAX_FINGERS_UP):
                    pinch_closed = True
                    gap = now - last_tap_time
                    if gap < DOUBLE_PINCH_WINDOW:
                        verdict = "CLICK!"
                        log(f"CLICK       gap={gap:.2f}s pinch={p:.2f} "
                            f"n_up={n_up} fingers={ups}")
                        last_tap_time = 0.0
                    else:
                        verdict = "tap 1..."
                        log(f"TAP-1       pinch={p:.2f} n_up={n_up} "
                            f"fingers={ups}")
                        last_tap_time = now
                elif pinch_closed and p > PINCH_OPEN:
                    pinch_closed = False
                    log(f"tap release pinch={p:.2f} n_up={n_up}")

            if time.time() - last_sample > 0.4:
                last_sample = time.time()
                log(f"sample pinch={p:.2f} n_up={n_up} fingers={ups} "
                    f"closed={pinch_closed} grab={grabbing}")

            color = (0, 0, 255) if (pinch_closed or grabbing) else (0, 255, 0)
            cv2.putText(frame, f"pinch {p:.2f}", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.2, color, 4)
            cv2.putText(frame, f"fingers up: {n_up}", (20, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 150, 0), 4)
            if verdict:
                cv2.putText(frame, verdict, (20, 260),
                            cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 200, 255), 4)

        cv2.putText(frame,
                    "double-pinch x5 (like opening a folder)  then ESC",
                    (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2)
        cv2.imshow("Pinch debug (ESC to quit)", frame)
        if cv2.waitKey(1) & 0xFF in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()
    LOG.close()


if __name__ == "__main__":
    main()
