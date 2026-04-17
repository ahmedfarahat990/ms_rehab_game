from __future__ import annotations

import sys
from pathlib import Path

import pygame

# Allow this module to be run directly during quick UI checks.
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_MENU, CYAN, RED, TEXT_MUTED, WHITE, get_font
from ms_rehab_game.ui.components import Button, TextInput, draw_text
from ms_rehab_game.ui.icons import render_icon


class LoginScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.username = TextInput(pygame.Rect(480, 280, 320, 48), "Username")
        self.password = TextInput(pygame.Rect(480, 350, 320, 48), "Password", password=True)
        self.message = ""
        self.message_color = RED
        button_width = self._auth_button_width("REGISTER", "register")
        gap = 20
        left_x = 480
        self.login_button = Button(pygame.Rect(left_x, 430, button_width, 50), "LOGIN", self._login, icon="login")
        self.register_button = Button(
            pygame.Rect(left_x + button_width + gap, 430, button_width, 50),
            "REGISTER",
            self._register,
            icon="register",
        )

    def _reflow_layout(self, surface_width: int) -> None:
        center_x = surface_width // 2

        self.username.rect.x = center_x - self.username.rect.width // 2
        self.password.rect.x = center_x - self.password.rect.width // 2

        gap = 20
        row_width = self.login_button.rect.width + gap + self.register_button.rect.width
        row_x = center_x - row_width // 2
        self.login_button.rect.x = row_x
        self.register_button.rect.x = row_x + self.login_button.rect.width + gap

    def _auth_button_width(self, label: str, icon: str) -> int:
        font = get_font(24, bold=True)
        icon_size = max(12, min(22, 50 - 14))
        icon_surface = render_icon(icon, icon_size, WHITE)
        icon_width = (icon_surface.get_width() + 8) if icon_surface is not None else 0
        text_width = font.size(label)[0]
        return max(150, text_width + icon_width + 28)

    def on_enter(self, **kwargs) -> None:
        self.message = ""

    def _login(self) -> None:
        user = self.manager.database.authenticate_user(self.username.text, self.password.text)
        if user:
            self.manager.current_user = user
            self.message = "Signed in successfully."
            self.message_color = CYAN
            self.manager.go_to("start")
        else:
            self.message = "Username or password is incorrect."
            self.message_color = RED

    def _register(self) -> None:
        if not self.username.text.strip() or not self.password.text:
            self.message = "Enter both a username and a password."
            self.message_color = RED
            return
        ok, msg = self.manager.database.create_user(self.username.text, self.password.text)
        self.message = msg
        self.message_color = CYAN if ok else RED

    def handle_event(self, events, gesture_data) -> None:
        for event in events:
            self.username.handle_event(event)
            self.password.handle_event(event)
            self.login_button.handle_event(event)
            self.register_button.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self._login()

    def draw(self, surface: pygame.Surface) -> None:
        self._reflow_layout(surface.get_width())
        surface.fill(BG_MENU)
        draw_text(surface, "MS RehabGame", 48, WHITE, (surface.get_width() // 2, 150), center=True, bold=True)
        draw_text(surface, "Fine motor and cognitive training", 20, TEXT_MUTED, (surface.get_width() // 2, 205), center=True)
        self.username.draw(surface)
        self.password.draw(surface)
        self.login_button.draw(surface)
        self.register_button.draw(surface)
        if self.message:
            message_y = self.register_button.rect.bottom + 28
            draw_text(surface, self.message, 22, self.message_color, (surface.get_width() // 2, message_y), center=True)
