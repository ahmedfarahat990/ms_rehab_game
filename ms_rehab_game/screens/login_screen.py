from __future__ import annotations

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_MENU, CYAN, RED, TEXT_MUTED, WHITE
from ms_rehab_game.ui.components import Button, TextInput, draw_text


class LoginScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.username = TextInput(pygame.Rect(480, 280, 320, 48), "Username")
        self.password = TextInput(pygame.Rect(480, 350, 320, 48), "Password", password=True)
        self.message = ""
        self.message_color = RED
        self.login_button = Button(pygame.Rect(480, 430, 150, 50), "LOGIN", self._login)
        self.register_button = Button(pygame.Rect(650, 430, 150, 50), "REGISTER", self._register)

    def on_enter(self, **kwargs) -> None:
        self.message = ""

    def _login(self) -> None:
        user = self.manager.database.authenticate_user(self.username.text, self.password.text)
        if user:
            self.manager.current_user = user
            self.message = "Login successful."
            self.message_color = CYAN
            self.manager.go_to("start")
        else:
            self.message = "Invalid username or password."
            self.message_color = RED

    def _register(self) -> None:
        if not self.username.text.strip() or not self.password.text:
            self.message = "Please enter a username and password."
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
        surface.fill(BG_MENU)
        draw_text(surface, "MS RehaGame", 48, WHITE, (surface.get_width() // 2, 150), center=True, bold=True)
        draw_text(surface, "Fine Motor & Cognitive Rehabilitation", 20, TEXT_MUTED, (surface.get_width() // 2, 205), center=True)
        self.username.draw(surface)
        self.password.draw(surface)
        self.login_button.draw(surface)
        self.register_button.draw(surface)
        if self.message:
            draw_text(surface, self.message, 22, self.message_color, (surface.get_width() // 2, 505), center=True)
