"""Hand tracking wrapper around MediaPipe Hands.

Returns, for a single hand, the 21 landmarks plus a couple of derived
values we care about: the index fingertip position and how "open" the
pinch is. Higher-level gesture decisions live in main.py.
"""

import mediapipe as mp
import numpy as np

# MediaPipe landmark indices we use
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
INDEX_PIP = 6          # index second knuckle (for "is finger up")
MIDDLE_TIP = 12
MIDDLE_PIP = 10
MIDDLE_MCP = 9         # middle-finger base knuckle: stable cursor anchor
RING_TIP = 16
RING_PIP = 14
PINKY_TIP = 20
PINKY_PIP = 18


class HandResult:
    def __init__(self, landmarks, handedness):
        # landmarks: list of (x, y, z) normalised to [0,1] on the frame
        self.landmarks = landmarks
        self.handedness = handedness

    def point(self, idx):
        return self.landmarks[idx]

    @property
    def index_tip(self):
        return self.landmarks[INDEX_TIP]

    def _norm_dist(self, a, b):
        """Distance between two landmarks, scaled by hand size so it's
        roughly the same whether your hand is near or far from the camera."""
        pa = np.array(self.landmarks[a][:2])
        pb = np.array(self.landmarks[b][:2])
        raw = np.linalg.norm(pa - pb)
        wrist = np.array(self.landmarks[WRIST][:2])
        ref_pt = np.array(self.landmarks[INDEX_PIP][:2])
        hand_size = np.linalg.norm(wrist - ref_pt) + 1e-6
        return raw / hand_size

    @property
    def pinch_distance(self):
        """Thumb tip <-> index tip (the click pinch)."""
        return self._norm_dist(THUMB_TIP, INDEX_TIP)

    @property
    def grab_distance(self):
        """How closed the whole hand is: max distance of thumb tip to the
        index/middle/ring tips. Small = all fingertips together (grab)."""
        return max(self._norm_dist(THUMB_TIP, INDEX_TIP),
                   self._norm_dist(THUMB_TIP, MIDDLE_TIP),
                   self._norm_dist(THUMB_TIP, RING_TIP))

    def fingers_up(self):
        """Rough count: is each of the 4 fingers (not thumb) extended?

        A finger is 'up' when its tip is higher (smaller y) than its PIP.
        Used only to detect the open-palm PAUSE gesture.
        """
        pairs = [
            (INDEX_TIP, INDEX_PIP),
            (MIDDLE_TIP, MIDDLE_PIP),
            (RING_TIP, RING_PIP),
            (PINKY_TIP, PINKY_PIP),
        ]
        return [self.landmarks[tip][1] < self.landmarks[pip][1] for tip, pip in pairs]

    @property
    def is_open_palm(self):
        return all(self.fingers_up())


class HandTracker:
    def __init__(self, detection_conf=0.7, tracking_conf=0.6):
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,               # lock onto ONE hand
            model_complexity=0,            # lite model: cooler for all-day use
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        self._draw = mp.solutions.drawing_utils
        self._style = mp.solutions.drawing_styles
        self._conn = mp.solutions.hands.HAND_CONNECTIONS

    def process(self, rgb_frame):
        """Return a HandResult or None if no confident hand found."""
        result = self._hands.process(rgb_frame)
        if not result.multi_hand_landmarks:
            return None, result
        lm = result.multi_hand_landmarks[0]
        landmarks = [(p.x, p.y, p.z) for p in lm.landmark]
        handed = None
        if result.multi_handedness:
            handed = result.multi_handedness[0].classification[0].label
        return HandResult(landmarks, handed), result

    def draw(self, bgr_frame, mp_result):
        """Draw the skeleton onto a BGR frame (for the preview window)."""
        if mp_result.multi_hand_landmarks:
            for lm in mp_result.multi_hand_landmarks:
                self._draw.draw_landmarks(
                    bgr_frame, lm, self._conn,
                    self._style.get_default_hand_landmarks_style(),
                    self._style.get_default_hand_connections_style(),
                )
