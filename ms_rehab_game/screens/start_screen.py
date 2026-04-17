from __future__ import annotations

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, CYAN, TEXT_MUTED, WHITE
from ms_rehab_game.ui.components import Button, draw_text, draw_text_in_rect


class StartScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.logout_button = Button(pygame.Rect(1040, 30, 180, 50), "LOG OUT", self.manager.logout, icon="logout")
        self.play_buttons = {
            "thumb_tango": Button(pygame.Rect(225, 500, 220, 50), "START", lambda: self._open_game("thumb_tango"), icon="play"),
            "mindful_tower": Button(pygame.Rect(835, 500, 220, 50), "START", lambda: self._open_game("mindful_tower"), icon="play"),
        }

    def _open_game(self, game_name: str) -> None:
        self.manager.selected_game = game_name
        self.manager.go_to("game_menu")

    def handle_event(self, events, gesture_data) -> None:
        for event in events:
            self.logout_button.handle_event(event)
            for button in self.play_buttons.values():
                button.handle_event(event)

    def _draw_card(self, surface: pygame.Surface, rect: pygame.Rect, title: str, lines: list[str], icon: str) -> None:
        pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
        pygame.draw.rect(surface, CYAN, rect, width=2, border_radius=12)
        draw_text(surface, icon, 64, WHITE, (rect.centerx, rect.y + 70), center=True)
        draw_text_in_rect(
            surface,
            title,
            28,
            WHITE,
            pygame.Rect(rect.x + 20, rect.y + 132, rect.width - 40, 40),
            center=True,
            bold=True,
            padding=0,
            min_size=16,
            truncate=True,
        )
        for index, line in enumerate(lines):
            draw_text_in_rect(
                surface,
                line,
                20,
                TEXT_MUTED,
                pygame.Rect(rect.x + 20, rect.y + 200 + index * 30, rect.width - 40, 28),
                center=True,
                padding=0,
                min_size=14,
                truncate=True,
            )

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        username = self.manager.current_user["username"] if self.manager.current_user else "Player"
        draw_text(surface, f"Welcome, {username}!", 40, WHITE, (70, 40), bold=True)
        self.logout_button.draw(surface)
        left_card = pygame.Rect(120, 150, 430, 420)
        right_card = pygame.Rect(730, 150, 430, 420)
        self._draw_card(
            surface,
            left_card,
            "Thumb Tango",
            ["Match each falling ball to the correct lane", "using thumb-to-finger opposition gestures."],
            "TT",
        )
        self._draw_card(
            surface,
            right_card,
            "Mindful Tower",
            ["Pick up blocks with a pinch and place them", "on matching target markers."],
            "MT",
        )
        self.play_buttons["thumb_tango"].draw(surface)
        self.play_buttons["mindful_tower"].draw(surface)
