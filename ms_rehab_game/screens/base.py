from __future__ import annotations

from typing import Any

import pygame

from ms_rehab_game.settings import BG_MENU


class BaseScreen:
    def __init__(self, manager: Any) -> None:
        self.manager = manager

    def on_enter(self, **kwargs: Any) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def handle_event(self, events: list[pygame.event.Event], gesture_data: Any) -> None:
        for _ in events:
            continue

    def update(self, dt: float, gesture_data: Any) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
