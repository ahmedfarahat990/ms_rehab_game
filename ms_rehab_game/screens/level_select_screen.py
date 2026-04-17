from __future__ import annotations

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, CYAN, TEXT_MUTED, THUMB_DURATIONS, WHITE, get_font
from ms_rehab_game.ui.components import Button, draw_text


class LevelSelectScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.selected_level = 1
        self.level_scrolls: dict[int, int] = {1: 0, 2: 0, 3: 0}
        self.level_viewports: dict[int, tuple[pygame.Rect, int]] = {}
        self.start_button = Button(pygame.Rect(530, 620, 220, 50), "START", self._confirm, icon="play")
        self.back_button = Button(pygame.Rect(530, 560, 220, 50), "BACK", lambda: self.manager.go_to("game_menu"), icon="back")

    def on_enter(self, **kwargs) -> None:
        self.selected_level = self.manager.selected_level
        self.level_scrolls = {1: 0, 2: 0, 3: 0}
        self.level_viewports.clear()

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
            elif event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                for level, (viewport, max_scroll) in self.level_viewports.items():
                    if max_scroll > 0 and viewport.collidepoint(mouse_pos):
                        current = self.level_scrolls.get(level, 0)
                        delta = event.x if event.x != 0 else -event.y
                        self.level_scrolls[level] = max(0, min(max_scroll, current + delta * 28))
                        break
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
        self.level_viewports.clear()
        draw_text(surface, "Choose Difficulty", 42, WHITE, (surface.get_width() // 2, 90), center=True, bold=True)
        descriptions = {
            1: ("Beginner", THUMB_DURATIONS[1] if self.manager.selected_game == "thumb_tango" else "Larger blocks with generous snap distance."),
            2: ("Intermediate", THUMB_DURATIONS[2] if self.manager.selected_game == "thumb_tango" else "More blocks with tighter snap distance."),
            3: ("Advanced", THUMB_DURATIONS[3] if self.manager.selected_game == "thumb_tango" else "Most blocks with strict snap precision."),
        }
        for level, rect in self._cards().items():
            pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
            pygame.draw.rect(surface, CYAN if self.selected_level == level else (80, 90, 105), rect, width=3, border_radius=12)
            title, description = descriptions[level]
            draw_text(surface, f"Level {level}", 28, WHITE, (rect.centerx, rect.y + 50), center=True, bold=True, max_width=rect.width - 30, truncate=True)
            draw_text(surface, title, 24, CYAN, (rect.centerx, rect.y + 95), center=True, max_width=rect.width - 30, truncate=True)

            scrollbar_gap = 6
            scrollbar_height = 6
            desc_clip = pygame.Rect(rect.x + 16, rect.y + 145, rect.width - 32, 58 - scrollbar_gap - scrollbar_height)
            desc_font = get_font(20)
            text_width = desc_font.size(description)[0]
            max_scroll = max(0, text_width - max(1, desc_clip.width - 4))
            scroll = max(0, min(max_scroll, self.level_scrolls.get(level, 0)))
            self.level_scrolls[level] = scroll
            self.level_viewports[level] = (desc_clip, max_scroll)

            text_y = desc_clip.y + (desc_clip.height - desc_font.get_height()) // 2
            draw_text(
                surface,
                description,
                20,
                TEXT_MUTED,
                (desc_clip.x + 2 - scroll, text_y),
                clip_rect=desc_clip,
            )

            if max_scroll > 0:
                track = pygame.Rect(desc_clip.x, desc_clip.bottom + scrollbar_gap, desc_clip.width, scrollbar_height)
                thumb_width = max(24, int(track.width * max(1, desc_clip.width) / max(1, text_width)))
                thumb_x = track.x + int((scroll / max_scroll) * (track.width - thumb_width)) if max_scroll else track.x
                thumb = pygame.Rect(thumb_x, track.y, thumb_width, track.height)
                pygame.draw.rect(surface, (65, 74, 92), track, border_radius=3)
                pygame.draw.rect(surface, CYAN, thumb, border_radius=3)
        self.back_button.draw(surface)
        self.start_button.draw(surface)
