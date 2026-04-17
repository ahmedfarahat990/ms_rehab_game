from __future__ import annotations

from pathlib import Path

import pygame

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"
FONTS_DIR = ASSETS_DIR / "fonts"
DB_PATH = DATA_DIR / "game.db"

for directory in (DATA_DIR, ASSETS_DIR, SOUNDS_DIR, FONTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
MIN_WIDTH = 960
MIN_HEIGHT = 540
FPS = 60
TITLE = "MS RehaGame"

BG_MENU = (13, 17, 23)
BG_GAME = (0, 0, 0)
BG_PANEL = (26, 26, 46)
BG_CARD = (20, 27, 39)
WHITE = (245, 245, 245)
TEXT_MUTED = (170, 180, 195)
BLACK = (0, 0, 0)
RED = (231, 76, 60)
GREEN = (46, 204, 113)
BLUE = (52, 152, 219)
YELLOW = (241, 196, 15)
PURPLE = (155, 89, 182)
ORANGE = (230, 126, 34)
GRAY = (120, 128, 140)
LIGHT_GRAY = (190, 196, 206)
DARK_GRAY = (63, 70, 84)
CYAN = (26, 188, 156)

GAME_COLORS = [RED, GREEN, BLUE, YELLOW]
COLOR_NAMES = ["red", "green", "blue", "yellow"]
LANE_TO_COLOR = {1: RED, 2: GREEN, 3: BLUE, 4: YELLOW}
LANE_TO_NAME = {1: "index", 2: "middle", 3: "ring", 4: "little"}

HAND_OPTIONS = ["left", "right"]
THUMB_TANGO_MODES = ["calm", "shuffle", "color_reveal", "memory"]
MINDFUL_TOWER_MODES = ["pinch_precision", "memory"]

THUMB_SPEEDS = {1: 120, 2: 200, 3: 300}
THUMB_DURATIONS = {
    1: "Slower moving balls and generous timing.",
    2: "Faster pace and stronger focus demands.",
    3: "Rapid reactions with minimal recovery time.",
}
TOWER_CONFIG = {
    1: {"count": 4, "cols": 2, "rows": 2, "block": 60, "snap": 50},
    2: {"count": 8, "cols": 2, "rows": 4, "block": 45, "snap": 35},
    3: {"count": 16, "cols": 4, "rows": 4, "block": 30, "snap": 20},
}

MEDAL_THRESHOLDS = {
    "thumb_tango": [("Platinum", 50000), ("Gold", 35000), ("Silver", 20000), ("Bronze", 0)],
    "mindful_tower": [("Platinum", 25000), ("Gold", 17000), ("Silver", 10000), ("Bronze", 0)],
}

ACHIEVEMENT_KEYS = [
    "first_game",
    "bronze",
    "silver",
    "gold",
    "platinum",
    "streak_5",
    "streak_10",
    "streak_15",
    "perfect_game",
    "days_10",
    "days_20",
    "days_30",
]

DEFAULT_USER_GAME_SETTINGS = {
    "controller_hand": "right",
    "duration_minutes": 3,
    "sound_enabled": True,
    "cognitive_mode": "calm",
    "show_tutorial": True,
}

WEBCAM_PREVIEW_SIZE = (200, 150)
FADE_DURATION = 0.3


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont("segoeui", size, bold=bold) or pygame.font.SysFont("arial", size, bold=bold)


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def medal_for_score(game_name: str, score: int) -> str:
    for medal, threshold in MEDAL_THRESHOLDS[game_name]:
        if score >= threshold:
            return medal
    return "Bronze"
