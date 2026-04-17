from __future__ import annotations

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_MENU, CYAN, HAND_OPTIONS, MINDFUL_TOWER_MODES, THUMB_TANGO_MODES, WHITE, format_mode_label
from ms_rehab_game.ui.components import Button, Slider, ToggleSwitch, draw_text, draw_text_in_rect


class SettingsScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.hand = "right"
        self.sound_toggle = ToggleSwitch(pygame.Rect(620, 340, 90, 36), True, "Sound Effects")
        self.duration_slider = Slider(pygame.Rect(420, 270, 420, 20), 2, 10, 3, step=1)
        self.mode_buttons: list[Button] = []
        self.save_button = Button(pygame.Rect(530, 620, 220, 50), "SAVE", self._save, icon="save")
        self.back_button = Button(pygame.Rect(530, 560, 220, 50), "BACK", lambda: self.manager.go_to("game_menu"), icon="back")

    def on_enter(self, **kwargs) -> None:
        settings = self.manager.database.get_user_game_settings(self.manager.current_user["id"], self.manager.selected_game)
        self.hand = settings["controller_hand"]
        self.sound_toggle.value = settings["sound_enabled"]
        self.duration_slider.value = settings["duration_minutes"]
        modes = THUMB_TANGO_MODES if self.manager.selected_game == "thumb_tango" else MINDFUL_TOWER_MODES
        current = settings["cognitive_mode"]
        self.mode_buttons = []
        for idx, mode in enumerate(modes):
            rect = pygame.Rect(350 + (idx % 2) * 300, 430 + (idx // 2) * 70, 240, 50)
            self.mode_buttons.append(Button(rect, format_mode_label(mode), lambda m=mode: self._set_mode(m), accent=CYAN))
        self.selected_mode = current if current in modes else modes[0]

    def _set_mode(self, mode: str) -> None:
        self.selected_mode = mode

    def _save(self) -> None:
        self.manager.database.save_user_game_settings(
            self.manager.current_user["id"],
            self.manager.selected_game,
            {
                "controller_hand": self.hand,
                "duration_minutes": self.duration_slider.value,
                "sound_enabled": self.sound_toggle.value,
                "cognitive_mode": self.selected_mode,
            },
        )
        self.manager.push_toast("Settings updated")
        self.manager.go_to("game_menu")

    def handle_event(self, events, gesture_data) -> None:
        hand_left = pygame.Rect(460, 180, 150, 50)
        hand_right = pygame.Rect(670, 180, 150, 50)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hand_left.collidepoint(event.pos):
                    self.hand = "left"
                elif hand_right.collidepoint(event.pos):
                    self.hand = "right"
            self.sound_toggle.handle_event(event)
            self.duration_slider.handle_event(event)
            self.save_button.handle_event(event)
            self.back_button.handle_event(event)
            for button in self.mode_buttons:
                button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        draw_text(surface, "Session Settings", 42, WHITE, (surface.get_width() // 2, 90), center=True, bold=True)
        draw_text(surface, "Controller Hand", 24, WHITE, (460, 140), bold=True)
        for idx, hand in enumerate(HAND_OPTIONS):
            rect = pygame.Rect(460 + idx * 210, 180, 150, 50)
            selected = self.hand == hand
            pygame.draw.rect(surface, CYAN if selected else (20, 27, 39), rect, border_radius=12)
            pygame.draw.rect(surface, WHITE if selected else (110, 120, 135), rect, width=2, border_radius=12)
            draw_text_in_rect(surface, hand.upper(), 22, WHITE, rect, center=True, bold=True, padding=8, min_size=14, truncate=True)
        draw_text(surface, f"Session Duration: {self.duration_slider.value} min", 24, WHITE, (420, 235), bold=True)
        self.duration_slider.draw(surface)
        self.sound_toggle.draw(surface)
        draw_text(surface, "Training Mode", 24, WHITE, (350, 395), bold=True)
        for button in self.mode_buttons:
            if button.text.lower().replace(" ", "_") == self.selected_mode:
                button.accent = CYAN
            else:
                button.accent = (90, 100, 115)
            button.draw(surface)
        self.back_button.draw(surface)
        self.save_button.draw(surface)
