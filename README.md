# Gesture Mouse

Control your real Mac cursor with hand gestures via the webcam. No extra
hardware — just your hand.

**Website:** https://deepkanchalia.github.io/gesture-mouse/

## Gestures

- **Move your hand** → cursor follows (anchored to your knuckle)
- **Hold still on a target ~2s** → ARMED (cursor locks onto the target)
- While armed:
  - **Flick index + thumb 3 times** → OPEN it (double-click)
  - **Close your hand and hold ~2s** → PICK UP · **open your hand** → DROP
- **Move away** → disarms, back to normal tracking
- **Hand out of frame** → cursor freezes where it is
- **ESC / q** (in the camera window) → quit

Arming first means nothing is ever clicked by accident — the cursor is
frozen on the target while you gesture, so taps can't drift off the icon.

A colored ring follows the cursor so you always know the state:
green = tracking · orange = armed / holding · red = carrying / click ·
gray = no hand. The camera window shows live coaching text
("HOLD STILL 1.2s / 2s to arm", "FLICK 2/3 to open"...).

## Install (one line)

```bash
curl -fsSL https://raw.githubusercontent.com/deepkanchalia/gesture-mouse/main/install.sh | bash
```

Or manually:

```bash
git clone https://github.com/deepkanchalia/gesture-mouse.git
cd gesture-mouse
./install.sh
```

Requires macOS + **Python 3.11 or 3.12** (MediaPipe does not support
newer). The installer checks for this and tells you how to get it if
missing (`brew install python@3.11`).

## Mac permissions (both required)

macOS blocks camera + mouse control until you allow them.

1. **Camera** — System Settings → Privacy & Security → **Camera** → enable for your Terminal.
2. **Accessibility** — System Settings → Privacy & Security → **Accessibility** → add & enable your Terminal.
   *Without this the window opens but the cursor will not move.*

The first run triggers the Camera prompt automatically. If the cursor
doesn't move, it's the Accessibility one — grant it and re-run.

**iPhone users:** macOS Continuity Camera can silently hijack the webcam
(you'll see your phone's camera, then "Lock iPhone To Resume"). Fix:
iPhone Settings → General → AirPlay & Continuity → Continuity Camera OFF.

## Run

```bash
cd gesture-mouse
./venv/bin/python main.py
```

## Emergency stop

Press **ESC** in the camera window, or take your hand out of the frame —
the cursor freezes instantly and nothing gets clicked.

## Tuning (in `main.py`)

- `ACTIVE_X0..Y1` — the inner camera box mapped to the full screen. Smaller box = less hand travel.
- `PINCH_CLOSE` / `PINCH_OPEN` — pinch sensitivity (hysteresis).
- `ARM_HOLD_SEC` / `DWELL_RADIUS_PX` — how long / how still to hold before arming.
- `OPEN_TAPS` / `TAPS_WINDOW_SEC` — flicks needed to open, and the time window.
- `GRAB_HOLD_SEC` — how long to keep the hand closed before it picks up.
- Smoothing: `min_cutoff` (lower = smoother, more lag) and `beta` (higher = snappier on fast moves).

If gestures misfire on your hand, run `./venv/bin/python pinch_debug.py` —
it logs your hand's real numbers to `pinch_log.txt` so you can tune to
data, not intuition.

## How it works

- **MediaPipe Hands** (lite model) reads 21 hand landmarks from the webcam at 640×360 — light enough for all-day use.
- A **One-Euro filter** smooths the cursor so it glides instead of jittering.
- **Quartz (Core Graphics)** moves the real macOS cursor and posts real clicks.
- The hover-arm state machine keeps movement and clicking separate, so a relaxed hand can never misfire a click.
