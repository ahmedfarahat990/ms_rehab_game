from __future__ import annotations

import math

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, CYAN, TEXT_MUTED, WHITE, get_font
from ms_rehab_game.ui.components import Button, draw_checkbox, draw_text


class TutorialScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.dont_show = False
        self.play_button = Button(pygame.Rect(470, 620, 340, 50), "I understand, let's play!", self._continue)

    def _continue(self) -> None:
        settings = self.manager.database.get_user_game_settings(self.manager.current_user["id"], self.manager.selected_game)
        settings["show_tutorial"] = not self.dont_show
        self.manager.database.save_user_game_settings(self.manager.current_user["id"], self.manager.selected_game, settings)
        self.manager.go_to(self.manager.selected_game, resume=False)

    def handle_event(self, events, gesture_data) -> None:
        checkbox_rect = pygame.Rect(420, 585, 24, 24)
        for event in events:
            self.play_button.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and checkbox_rect.collidepoint(event.pos):
                self.dont_show = not self.dont_show

    def update(self, dt, gesture_data) -> None:
        self.phase = getattr(self, "phase", 0.0) + dt

    def _content(self) -> dict[str, object]:
        if self.manager.selected_game == "thumb_tango":
            return {
                "subtitle": "Touch your thumb to a finger to choose the lane for each falling ball.",
                "goal": [
                    "Wait for the ball to reach the split zone in the middle.",
                    "Make one thumb-to-finger touch while the ball is in that zone.",
                    "Send the ball to the lane that matches its color.",
                ],
                "controls_title": "Finger to lane",
                "controls": [
                    "Index -> lane 1",
                    "Middle -> lane 2",
                    "Ring -> lane 3",
                    "Little -> lane 4",
                ],
                "tips": [
                    "Calm: colors stay visible.",
                    "Shuffle: lanes change position.",
                    "Memory: second hand shows a short hint.",
                    "+100 correct, -30 wrong.",
                ],
                "preview_label": "Touch thumb to one finger",
            }
        return {
            "subtitle": "Pinch a block, move it, and place it on the matching target spot.",
            "goal": [
                "Study the target tower at the start.",
                "Pinch over a block to pick it up.",
                "Move it to the correct marker, then open your fingers to drop it.",
            ],
            "controls_title": "Pinch action",
            "controls": [
                "Close thumb + index = pick up",
                "Keep pinch closed = move block",
                "Open fingers = drop block",
                "Wrong color returns to tray",
            ],
            "tips": [
                "Pinch Precision: target stays visible.",
                "Memory: second hand shows a short hint.",
                "Place carefully near the marker.",
                "+100 correct, -30 wrong.",
            ],
            "preview_label": "Pinch to pick up, open to drop",
        }

    def _draw_card(self, surface: pygame.Surface, rect: pygame.Rect, title: str, lines: list[str]) -> None:
        pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
        pygame.draw.rect(surface, CYAN, rect, width=2, border_radius=12)
        draw_text(surface, title, 22, CYAN, (rect.x + 20, rect.y + 16), bold=True)
        font = get_font(18)
        y = rect.y + 54
        for line in lines:
            rendered = font.render(f"- {line}", True, TEXT_MUTED)
            surface.blit(rendered, (rect.x + 24, y))
            y += 38

    def _draw_animation(self, surface: pygame.Surface, rect: pygame.Rect, label: str) -> None:
        pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
        pygame.draw.rect(surface, CYAN, rect, width=2, border_radius=12)
        draw_text(surface, "Gesture Preview", 24, WHITE, (rect.centerx, rect.y + 18), center=True, bold=True)
        phase = getattr(self, "phase", 0.0)
        if self.manager.selected_game == "thumb_tango":
            center = (rect.centerx, rect.centery + 10)
            pygame.draw.circle(surface, WHITE, center, 35, 3)
            for idx in range(4):
                angle = math.pi * (0.9 - idx * 0.2)
                tip = (center[0] + int(math.cos(angle) * 95), center[1] - int(math.sin(angle) * 85))
                pygame.draw.line(surface, WHITE, center, tip, 4)
            active = int((phase * 2) % 4)
            points = [
                (rect.centerx - 78, rect.centery - 88),
                (rect.centerx - 25, rect.centery - 115),
                (rect.centerx + 28, rect.centery - 95),
                (rect.centerx + 78, rect.centery - 60),
            ]
            pygame.draw.circle(surface, CYAN, points[active], 14)
            pygame.draw.line(surface, CYAN, (rect.centerx - 35, rect.centery + 36), points[active], 5)
        else:
            tray = pygame.Rect(rect.x + 48, rect.centery - 18, 120, 80)
            target = pygame.Rect(rect.right - 168, rect.centery - 58, 120, 120)
            pygame.draw.rect(surface, (90, 90, 90), tray, width=2, border_radius=8)
            pygame.draw.rect(surface, (90, 90, 90), target, width=2, border_radius=8)
            t = (math.sin(phase * 2) + 1) / 2
            x = int(tray.centerx + (target.centerx - tray.centerx) * t)
            y = int(tray.centery + (target.centery - tray.centery) * t)
            pygame.draw.rect(surface, CYAN, pygame.Rect(x - 22, y - 22, 44, 44), border_radius=8)
            pygame.draw.circle(surface, WHITE, (x, y - 34), 10, 2)
            pygame.draw.circle(surface, WHITE, (x + 14, y - 27), 10, 2)
        draw_text(surface, label, 18, TEXT_MUTED, (rect.centerx, rect.bottom - 38), center=True)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        content = self._content()

        draw_text(surface, "How to Play", 42, WHITE, (surface.get_width() // 2, 66), center=True, bold=True)
        draw_text(surface, content["subtitle"], 20, TEXT_MUTED, (surface.get_width() // 2, 112), center=True)

        self._draw_card(surface, pygame.Rect(90, 165, 610, 150), "What to do", content["goal"])
        self._draw_card(surface, pygame.Rect(90, 335, 295, 180), content["controls_title"], content["controls"])
        self._draw_card(surface, pygame.Rect(405, 335, 295, 180), "Quick tips", content["tips"])
        self._draw_animation(surface, pygame.Rect(745, 185, 420, 330), content["preview_label"])

        draw_text(surface, "Pause works only after your first action.", 18, TEXT_MUTED, (955, 535), center=True)

        checkbox_rect = pygame.Rect(420, 585, 24, 24)
        draw_checkbox(surface, checkbox_rect, self.dont_show, "Don't show again")
        self.play_button.draw(surface)
