from __future__ import annotations

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, CYAN, TEXT_MUTED, THUMB_DURATIONS, WHITE
from ms_rehab_game.ui.components import Button, draw_text


class LevelSelectScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.selected_level = 1
        self.start_button = Button(pygame.Rect(530, 620, 220, 50), "START", self._confirm)
        self.back_button = Button(pygame.Rect(530, 560, 220, 50), "BACK", lambda: self.manager.go_to("game_menu"))

    def on_enter(self, **kwargs) -> None:
        self.selected_level = self.manager.selected_level

    def _confirm(self) -> None:
        self.manager.selected_level = self.selected_level
        settings = self.manager.database.get_user_game_settings(self.manager.current_user["id"], self.manager.selected_game)
        if settings["show_tutorial"]:
            self.manager.go_to("tutorial")
        else:
            self.manager.go_to(self.manager.selected_game, resume=False)

    def handle_event(self, events, gesture_data) -> None:
        cards = self._cards()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for level, rect in cards.items():
                    if rect.collidepoint(event.pos):
                        self.selected_level = level
            self.start_button.handle_event(event)
            self.back_button.handle_event(event)

    def _cards(self) -> dict[int, pygame.Rect]:
        return {
            1: pygame.Rect(120, 220, 320, 250),
            2: pygame.Rect(480, 220, 320, 250),
            3: pygame.Rect(840, 220, 320, 250),
        }

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        draw_text(surface, "Select Level", 42, WHITE, (surface.get_width() // 2, 90), center=True, bold=True)
        descriptions = {
            1: ("Beginner", THUMB_DURATIONS[1] if self.manager.selected_game == "thumb_tango" else "Large blocks and forgiving snap targets."),
            2: ("Intermediate", THUMB_DURATIONS[2] if self.manager.selected_game == "thumb_tango" else "More pieces and tighter control."),
            3: ("Advanced", THUMB_DURATIONS[3] if self.manager.selected_game == "thumb_tango" else "Dense patterns with precision snapping."),
        }
        for level, rect in self._cards().items():
            pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
            pygame.draw.rect(surface, CYAN if self.selected_level == level else (80, 90, 105), rect, width=3, border_radius=12)
            title, description = descriptions[level]
            draw_text(surface, f"Level {level}", 28, WHITE, (rect.centerx, rect.y + 50), center=True, bold=True)
            draw_text(surface, title, 24, CYAN, (rect.centerx, rect.y + 95), center=True)
            words = description.split()
            lines = [" ".join(words[:6]), " ".join(words[6:12]), " ".join(words[12:])]
            for idx, line in enumerate([line for line in lines if line.strip()]):
                draw_text(surface, line, 20, TEXT_MUTED, (rect.centerx, rect.y + 150 + idx * 28), center=True)
        self.back_button.draw(surface)
        self.start_button.draw(surface)
