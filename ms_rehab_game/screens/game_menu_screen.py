from __future__ import annotations

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_MENU, CYAN, TEXT_MUTED, WHITE
from ms_rehab_game.ui.components import Button, draw_text


class GameMenuScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.buttons: list[Button] = []
        self.resume_button: Button | None = None

    def on_enter(self, **kwargs) -> None:
        game_name = self.manager.selected_game
        user_id = self.manager.current_user["id"]
        paused = self.manager.database.get_paused_session(user_id, game_name)
        self.buttons = [
            Button(pygame.Rect(530, 220, 220, 50), "NEW GAME", lambda: self.manager.go_to("level_select")),
            Button(
                pygame.Rect(530, 290, 220, 50),
                "RESUME",
                lambda: self.manager.go_to(game_name, resume=True),
                enabled=paused is not None,
            ),
            Button(pygame.Rect(530, 360, 220, 50), "STATISTICS", lambda: self.manager.go_to("statistics")),
            Button(pygame.Rect(530, 430, 220, 50), "SETTINGS", lambda: self.manager.go_to("settings")),
            Button(pygame.Rect(530, 500, 220, 50), "BACK", lambda: self.manager.go_to("start")),
        ]

    def handle_event(self, events, gesture_data) -> None:
        for event in events:
            for button in self.buttons:
                button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        title = "Thumb Tango" if self.manager.selected_game == "thumb_tango" else "Mindful Tower"
        draw_text(surface, title, 42, WHITE, (surface.get_width() // 2, 110), center=True, bold=True)
        draw_text(surface, "Pick up where you left off or start a new training session.", 20, TEXT_MUTED, (surface.get_width() // 2, 160), center=True)
        for button in self.buttons:
            button.draw(surface)
