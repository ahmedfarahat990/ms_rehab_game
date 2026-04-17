from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

import cv2
import numpy as np
import pygame

from ms_rehab_game.settings import ASSETS_DIR, WEBCAM_PREVIEW_SIZE, clamp

MODEL_DIR = ASSETS_DIR / "models"
MODEL_PATH = MODEL_DIR / "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def detect_pinch(landmarks_px: list[tuple[int, int]]) -> dict[str, Any]:
    thumb = landmarks_px[4]
    index = landmarks_px[8]
    distance = _distance(thumb, index)
    midpoint = (int((thumb[0] + index[0]) / 2), int((thumb[1] + index[1]) / 2))
    return {
        "pinching": distance < 40,
        "position": midpoint,
        "pinch_strength": clamp(1.0 - (distance / 40.0), 0.0, 1.0),
        "distance": distance,
    }


def detect_thumb_opposition(landmarks_px: list[tuple[int, int]]) -> dict[str, Any]:
    thumb = landmarks_px[4]
    targets = {"index": 8, "middle": 12, "ring": 16, "little": 20}
    lane_map = {"index": 1, "middle": 2, "ring": 3, "little": 4}
    matched_finger = None
    matched_distance = float("inf")
    for finger, tip_idx in targets.items():
        distance = _distance(thumb, landmarks_px[tip_idx])
        if distance < 40 and distance < matched_distance:
            matched_finger = finger
            matched_distance = distance
    return {
        "active": matched_finger is not None,
        "finger": matched_finger,
        "lane": lane_map.get(matched_finger),
        "distance": None if matched_finger is None else matched_distance,
    }


def detect_non_controlling_hand_press(landmarks_px: list[tuple[int, int]], frame_size: tuple[int, int]) -> bool:
    palm_indices = [0, 5, 9, 13, 17]
    palm_x = sum(landmarks_px[idx][0] for idx in palm_indices) / len(palm_indices)
    palm_y = sum(landmarks_px[idx][1] for idx in palm_indices) / len(palm_indices)
    width, height = frame_size
    return 0 <= palm_x <= width and 0 <= palm_y <= height


def ensure_hand_model() -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


@dataclass
class GestureSnapshot:
    hands: list[dict[str, Any]] = field(default_factory=list)
    controlling_hand: dict[str, Any] | None = None
    secondary_hand_hint: bool = False
    swipe: str | None = None
    frame_surface: pygame.Surface | None = None
    timestamp: float = field(default_factory=time.time)
    status: str = "ok"


class _LegacyHandsBackend:
    def __init__(self) -> None:
        import mediapipe as mp

        self.mp_hands = mp.solutions.hands
        self.drawer = mp.solutions.drawing_utils
        self.connection_style = self.mp_hands.HAND_CONNECTIONS
        self.detector = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )

    def process(self, frame_bgr: np.ndarray) -> tuple[list[dict[str, Any]], np.ndarray]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.detector.process(rgb)
        height, width = frame_bgr.shape[:2]
        hands_data: list[dict[str, Any]] = []
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label.lower()
                landmarks_px = [(int(lm.x * width), int(lm.y * height)) for lm in hand_landmarks.landmark]
                hands_data.append(
                    {
                        "label": label,
                        "landmarks_px": landmarks_px,
                        "pinch": detect_pinch(landmarks_px),
                        "opposition": detect_thumb_opposition(landmarks_px),
                    }
                )
                self.drawer.draw_landmarks(frame_bgr, hand_landmarks, self.connection_style)
        return hands_data, frame_bgr

    def close(self) -> None:
        self.detector.close()


class _TasksHandsBackend:
    def __init__(self) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.vision import drawing_utils

        model_path = ensure_hand_model()
        self.mp = mp
        self.drawer = drawing_utils
        self.connections = vision.HandLandmarksConnections.HAND_CONNECTIONS
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def process(self, frame_bgr: np.ndarray) -> tuple[list[dict[str, Any]], np.ndarray]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(time.time() * 1000)
        result = self.detector.detect_for_video(mp_image, timestamp_ms)
        height, width = frame_bgr.shape[:2]
        hands_data: list[dict[str, Any]] = []
        for landmarks, handedness_list in zip(result.hand_landmarks, result.handedness):
            label = handedness_list[0].category_name.lower()
            landmarks_px = [(int(lm.x * width), int(lm.y * height)) for lm in landmarks]
            hands_data.append(
                {
                    "label": label,
                    "landmarks_px": landmarks_px,
                    "pinch": detect_pinch(landmarks_px),
                    "opposition": detect_thumb_opposition(landmarks_px),
                }
            )
            self.drawer.draw_landmarks(frame_bgr, landmarks, self.connections)
        return hands_data, frame_bgr

    def close(self) -> None:
        self.detector.close()


def create_backend() -> tuple[Any | None, str]:
    try:
        import mediapipe as mp

        if hasattr(mp, "solutions"):
            return _LegacyHandsBackend(), "legacy"
        return _TasksHandsBackend(), "tasks"
    except Exception as exc:
        return None, f"error: {exc}"


class MediaPipeGestureThread:
    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = False
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()
        self.latest = GestureSnapshot(status="initializing")
        self.wrist_history: deque[tuple[int, int]] = deque(maxlen=15)
        self.backend, self.backend_name = create_backend()
        if self.backend is None:
            self.latest.status = self.backend_name

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)
        if self.cap.isOpened():
            self.cap.release()
        if self.backend is not None:
            self.backend.close()

    def get_latest(self) -> GestureSnapshot:
        with self.lock:
            return self.latest

    def _detect_swipe(self) -> str | None:
        if len(self.wrist_history) < self.wrist_history.maxlen:
            return None
        delta_x = self.wrist_history[-1][0] - self.wrist_history[0][0]
        if delta_x > 150:
            self.wrist_history.clear()
            return "right"
        if delta_x < -150:
            self.wrist_history.clear()
            return "left"
        return None

    def _make_surface(self, frame_bgr: np.ndarray) -> pygame.Surface:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, WEBCAM_PREVIEW_SIZE)
        surface = pygame.image.frombuffer(rgb.tobytes(), WEBCAM_PREVIEW_SIZE, "RGB")
        return surface.copy()

    def _run(self) -> None:
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            hands_data: list[dict[str, Any]] = []
            controlling_hand = None
            secondary_hint = False
            swipe = None
            status = self.backend_name if self.backend is not None else self.latest.status

            if self.backend is not None:
                try:
                    hands_data, frame = self.backend.process(frame)
                    if hands_data:
                        controlling_hand = hands_data[0]
                        self.wrist_history.append(controlling_hand["landmarks_px"][0])
                        swipe = self._detect_swipe()
                    if len(hands_data) > 1:
                        secondary_hint = detect_non_controlling_hand_press(
                            hands_data[1]["landmarks_px"],
                            (frame.shape[1], frame.shape[0]),
                        )
                except Exception as exc:
                    status = f"error: {exc}"

            snapshot = GestureSnapshot(
                hands=hands_data,
                controlling_hand=controlling_hand,
                secondary_hand_hint=secondary_hint,
                swipe=swipe,
                frame_surface=self._make_surface(frame),
                status=status,
            )
            with self.lock:
                self.latest = snapshot
            time.sleep(0.01)
