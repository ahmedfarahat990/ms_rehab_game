from __future__ import annotations

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, TEXT_MUTED, WHITE
from ms_rehab_game.ui.components import Button, draw_text


class PauseScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.resume_button = Button(pygame.Rect(530, 380, 220, 50), "RESUME", self._resume)
        self.exit_button = Button(pygame.Rect(530, 450, 220, 50), "EXIT TO MENU", self._exit)
        self.payload = {}

    def on_enter(self, **kwargs) -> None:
        self.payload = kwargs

    def _resume(self) -> None:
        self.manager.go_to(self.manager.selected_game, resume=True, from_pause=True)

    def _exit(self) -> None:
        self.manager.go_to("game_menu")

    def handle_event(self, events, gesture_data) -> None:
        for event in events:
            self.resume_button.handle_event(event)
            self.exit_button.handle_event(event)
        if gesture_data.swipe == "left":
            self._resume()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        panel = pygame.Rect(380, 170, 520, 380)
        pygame.draw.rect(surface, BG_CARD, panel, border_radius=12)
        pygame.draw.rect(surface, WHITE, panel, width=2, border_radius=12)
        draw_text(surface, "Paused", 40, WHITE, (panel.centerx, panel.y + 50), center=True, bold=True)
        draw_text(surface, f"Score: {self.payload.get('score', 0)}", 26, WHITE, (panel.centerx, panel.y + 125), center=True)
        draw_text(surface, f"Time Remaining: {int(self.payload.get('time_remaining', 0))}s", 24, TEXT_MUTED, (panel.centerx, panel.y + 170), center=True)
        draw_text(surface, f"Level: {self.payload.get('level', 1)}", 24, TEXT_MUTED, (panel.centerx, panel.y + 205), center=True)
        self.resume_button.draw(surface)
        self.exit_button.draw(surface)
