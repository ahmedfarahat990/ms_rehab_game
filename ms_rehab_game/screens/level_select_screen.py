from __future__ import annotations

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, CYAN, TEXT_MUTED, THUMB_DURATIONS, WHITE, get_font
from ms_rehab_game.ui.components import Button, draw_text


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """Break *text* into lines that each fit within *max_width* pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class LevelSelectScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.selected_level = 1
        self.start_button = Button(pygame.Rect(530, 660, 220, 50), "START", self._confirm, icon="play")
        self.back_button  = Button(pygame.Rect(530, 600, 220, 50), "BACK",  lambda: self.manager.go_to("game_menu"), icon="back")

    def on_enter(self, **kwargs) -> None:
        self.selected_level = self.manager.selected_level

    def _confirm(self) -> None:
        self.manager.selected_level = self.selected_level
        settings = self.manager.database.get_user_game_settings(
            self.manager.current_user["id"], self.manager.selected_game
        )
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
        # Taller cards so wrapped description text always fits without scrolling
        return {
            1: pygame.Rect(100, 200, 340, 320),
            2: pygame.Rect(480, 200, 340, 320),
            3: pygame.Rect(860, 200, 340, 320),
        }

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        draw_text(surface, "Choose Difficulty", 42, WHITE, (surface.get_width() // 2, 90), center=True, bold=True)

        descriptions = {
            1: (
                "Beginner",
                THUMB_DURATIONS[1] if self.manager.selected_game == "thumb_tango"
                else "Larger blocks with generous snap distance. Ideal for first-time players or those building confidence.",
            ),
            2: (
                "Intermediate",
                THUMB_DURATIONS[2] if self.manager.selected_game == "thumb_tango"
                else "More blocks with tighter snap distance. A balanced challenge for players with some practice.",
            ),
            3: (
                "Advanced",
                THUMB_DURATIONS[3] if self.manager.selected_game == "thumb_tango"
                else "Most blocks with strict snap precision. Fast-paced and demanding — for experienced players.",
            ),
        }

        desc_font = get_font(18)
        line_h    = desc_font.get_height() + 4

        for level, rect in self._cards().items():
            pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
            pygame.draw.rect(
                surface,
                CYAN if self.selected_level == level else (80, 90, 105),
                rect, width=3, border_radius=12,
            )

            label, description = descriptions[level]
            draw_text(surface, f"Level {level}", 28, WHITE,
                      (rect.centerx, rect.y + 48), center=True, bold=True,
                      max_width=rect.width - 30, truncate=True)
            draw_text(surface, label, 22, CYAN,
                      (rect.centerx, rect.y + 92), center=True,
                      max_width=rect.width - 30, truncate=True)

            # Progress-bar accent at the bottom of the card
            bar_rect = pygame.Rect(rect.x + 20, rect.bottom - 22, rect.width - 40, 6)
            fill_w   = int(bar_rect.width * (level / 3))
            pygame.draw.rect(surface, (50, 60, 75),   bar_rect,                                  border_radius=3)
            pygame.draw.rect(surface, CYAN,            pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height), border_radius=3)

            # Word-wrapped description — no scrollbar needed
            desc_area_x = rect.x + 18
            desc_area_w = rect.width - 36
            desc_area_y = rect.y + 130
            desc_area_bottom = bar_rect.y - 10

            lines = _wrap_text(description, desc_font, desc_area_w)
            y = desc_area_y
            for line in lines:
                if y + line_h > desc_area_bottom:
                    # Show ellipsis on the last visible line if text is still cut
                    surf = desc_font.render("…", True, TEXT_MUTED)
                    surface.blit(surf, (desc_area_x, y - line_h))
                    break
                surf = desc_font.render(line, True, TEXT_MUTED)
                surface.blit(surf, (desc_area_x, y))
                y += line_h

        self.back_button.draw(surface)
        self.start_button.draw(surface)
