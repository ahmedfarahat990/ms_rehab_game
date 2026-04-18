from __future__ import annotations

import math

import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, CYAN, TEXT_MUTED, WHITE, get_font
from ms_rehab_game.ui.components import Button, draw_checkbox, draw_text, draw_text_in_rect


class TutorialScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.dont_show = False
        self.back_button = Button(pygame.Rect(90, 620, 170, 50), "BACK", lambda: self.manager.go_to("game_menu"), icon="back")
        self.home_button = Button(pygame.Rect(1020, 620, 170, 50), "HOME", lambda: self.manager.go_to("start"), icon="menu")
        self.play_button = Button(pygame.Rect(470, 620, 340, 50), "START TRAINING", self._continue, icon="play")
        self.card_scrolls: dict[str, int] = {}
        self.card_viewports: dict[str, tuple[pygame.Rect, int]] = {}

    def _layout_action_buttons(self, surface_width: int) -> None:
        margin = 90
        self.back_button.rect.topleft = (margin, self.back_button.rect.y)
        self.home_button.rect.topright = (surface_width - margin, self.home_button.rect.y)
        self.play_button.rect.centerx = surface_width // 2

    def on_enter(self, **kwargs) -> None:
        self.card_scrolls.clear()
        self.card_viewports.clear()

    def _continue(self) -> None:
        settings = self.manager.database.get_user_game_settings(self.manager.current_user["id"], self.manager.selected_game)
        settings["show_tutorial"] = not self.dont_show
        self.manager.database.save_user_game_settings(self.manager.current_user["id"], self.manager.selected_game, settings)
        self.manager.go_to(self.manager.selected_game, resume=False)

    def handle_event(self, events, gesture_data) -> None:
        checkbox_rect = pygame.Rect(420, 585, 24, 24)
        for event in events:
            self.back_button.handle_event(event)
            self.home_button.handle_event(event)
            self.play_button.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and checkbox_rect.collidepoint(event.pos):
                self.dont_show = not self.dont_show
            elif event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                for card_key, (viewport, max_scroll) in self.card_viewports.items():
                    if max_scroll > 0 and viewport.collidepoint(mouse_pos):
                        current = self.card_scrolls.get(card_key, 0)
                        self.card_scrolls[card_key] = max(0, min(max_scroll, current - event.y * 28))
                        break

    def update(self, dt, gesture_data) -> None:
        self.phase = getattr(self, "phase", 0.0) + dt

    def _content(self) -> dict[str, object]:
        if self.manager.selected_game == "thumb_tango":
            return {
                "subtitle": "Use one thumb-to-finger touch to send each falling ball into the correct lane.",
                "goal": [
                    "Wait for a ball to enter the split zone.",
                    "Make one thumb-to-finger touch while it is in the zone.",
                    "Match the ball color to the lane color.",
                ],
                "controls_title": "Finger Mapping",
                "controls": [
                    "Index finger -> lane 1",
                    "Middle finger -> lane 2",
                    "Ring finger -> lane 3",
                    "Little finger -> lane 4",
                ],
                "tips": [
                    "Calm: lane colors stay visible.",
                    "Shuffle Lanes: lane colors reshuffle every 10s.",
                    "Color Reveal: ball color appears near the split zone.",
                    "Memory: colors hide after preview; hint cue can reveal briefly.",
                ],
                "preview_label": "Touch thumb to one finger",
            }
        return {
            "subtitle": "Pinch to pick up each block, move it, and drop it on a matching target marker.",
            "goal": [
                "Check the target pattern before placing blocks.",
                "Pinch on a block to pick it up.",
                "Move to a matching marker and open fingers to drop.",
            ],
            "controls_title": "Pinch Controls",
            "controls": [
                "Close thumb + index: pick up",
                "Hold pinch: move block",
                "Open fingers: drop block",
                "Wrong match: block returns to tray",
            ],
            "tips": [
                "Pinch Precision: target pattern stays visible.",
                "Memory: target preview hides after countdown.",
                "Second-hand cue can briefly reveal target.",
                "Score: +100 correct, -30 miss.",
            ],
            "preview_label": "Pinch to pick up, open to drop",
        }

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int, first_prefix: str = "", next_prefix: str = "") -> list[str]:
        words = text.split()
        if not words:
            return [first_prefix.strip()]

        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            prefix = first_prefix if not lines else next_prefix
            preview = f"{prefix}{candidate}"
            if current and font.size(preview)[0] > max_width:
                lines.append(f"{prefix}{current}" if not lines else f"{next_prefix}{current}")
                current = word
            else:
                current = candidate

        prefix = first_prefix if not lines else next_prefix
        lines.append(f"{prefix}{current}")
        return lines

    def _draw_card(self, surface: pygame.Surface, rect: pygame.Rect, title: str, lines: list[str], card_key: str) -> None:
        pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
        pygame.draw.rect(surface, CYAN, rect, width=2, border_radius=12)
        draw_text_in_rect(
            surface,
            title,
            22,
            CYAN,
            pygame.Rect(rect.x + 18, rect.y + 12, rect.width - 36, 30),
            center=False,
            bold=True,
            padding=0,
            min_size=14,
            truncate=True,
        )

        scrollbar_gap = 10
        scrollbar_width = 6
        content_clip = pygame.Rect(rect.x + 18, rect.y + 48, rect.width - 36 - scrollbar_gap - scrollbar_width, rect.height - 58)
        font = get_font(18)
        line_height = 26

        wrapped_lines: list[str] = []
        for line in lines:
            wrapped_lines.extend(self._wrap_text(line, font, content_clip.width - 4, first_prefix="- ", next_prefix="  "))

        content_height = max(line_height, len(wrapped_lines) * line_height)
        max_scroll = max(0, content_height - content_clip.height)
        scroll = max(0, min(max_scroll, self.card_scrolls.get(card_key, 0)))
        self.card_scrolls[card_key] = scroll
        self.card_viewports[card_key] = (content_clip, max_scroll)

        for idx, line in enumerate(wrapped_lines):
            y = content_clip.y - scroll + idx * line_height
            draw_text(
                surface,
                line,
                18,
                TEXT_MUTED,
                (content_clip.x + 2, y),
                max_width=content_clip.width - 4,
                truncate=True,
                clip_rect=content_clip,
            )

        if max_scroll > 0:
            track = pygame.Rect(content_clip.right + scrollbar_gap, content_clip.y, scrollbar_width, content_clip.height)
            thumb_height = max(24, int(track.height * content_clip.height / content_height))
            thumb_y = track.y + int((scroll / max_scroll) * (track.height - thumb_height)) if max_scroll else track.y
            thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_height)
            pygame.draw.rect(surface, (65, 74, 92), track, border_radius=3)
            pygame.draw.rect(surface, CYAN, thumb, border_radius=3)

    def _draw_animation(self, surface: pygame.Surface, rect: pygame.Rect, label: str) -> None:
        pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
        pygame.draw.rect(surface, CYAN, rect, width=2, border_radius=12)
        draw_text(surface, "Gesture Preview", 24, WHITE, (rect.centerx, rect.y + 18), center=True, bold=True)
        phase = getattr(self, "phase", 0.0)
        if self.manager.selected_game == "thumb_tango":
            lane_x = [rect.centerx - 125, rect.centerx - 40, rect.centerx + 40, rect.centerx + 125]
            split_point = (rect.centerx, rect.y + 120)
            lane_y = rect.bottom - 118
            for x in lane_x:
                pygame.draw.line(surface, (95, 105, 122), split_point, (x, lane_y), 2)
                pygame.draw.circle(surface, (85, 95, 112), (x, lane_y), 14, 2)

            cycle = 2.8
            lane_index = int((phase / cycle) % 4)
            t = (phase % cycle) / cycle
            if t < 0.45:
                interp = t / 0.45
                bx = split_point[0]
                by = int(rect.y + 74 + (split_point[1] - (rect.y + 74)) * interp)
            else:
                interp = (t - 0.45) / 0.55
                bx = int(split_point[0] + (lane_x[lane_index] - split_point[0]) * interp)
                by = int(split_point[1] + (lane_y - split_point[1]) * interp)
            pygame.draw.circle(surface, WHITE, (bx, by), 2)
            pygame.draw.circle(surface, CYAN, (bx, by), 12)
            pygame.draw.circle(surface, WHITE, (bx, by), 12, 2)

            hand_center = (rect.centerx, rect.bottom - 100)
            palm = pygame.Rect(hand_center[0] - 42, hand_center[1] - 6, 84, 46)
            pygame.draw.ellipse(surface, WHITE, palm, 2)
            finger_tips = [
                (lane_x[0], hand_center[1] - 52),
                (lane_x[1], hand_center[1] - 68),
                (lane_x[2], hand_center[1] - 68),
                (lane_x[3], hand_center[1] - 52),
            ]
            for idx, point in enumerate(finger_tips):
                color = CYAN if idx == lane_index else WHITE
                pygame.draw.line(surface, WHITE, (point[0], hand_center[1] - 6), point, 3)
                pygame.draw.circle(surface, color, point, 8 if idx == lane_index else 6, 2)
            thumb_tip = (hand_center[0] - 56, hand_center[1] + 2)
            pygame.draw.line(surface, CYAN, thumb_tip, finger_tips[lane_index], 4)
            pygame.draw.circle(surface, CYAN, thumb_tip, 6)
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
        draw_text(surface, label, 18, TEXT_MUTED, (rect.centerx, rect.bottom - 38), center=True, max_width=rect.width - 30, truncate=True)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        self._layout_action_buttons(surface.get_width())
        self.card_viewports.clear()
        content = self._content()

        draw_text(surface, "How to Play", 42, WHITE, (surface.get_width() // 2, 66), center=True, bold=True)
        draw_text(surface, content["subtitle"], 20, TEXT_MUTED, (surface.get_width() // 2, 112), center=True)

        self._draw_card(surface, pygame.Rect(90, 165, 610, 150), "What to Do", content["goal"], "goal")
        self._draw_card(surface, pygame.Rect(90, 335, 295, 180), content["controls_title"], content["controls"], "controls")
        self._draw_card(surface, pygame.Rect(405, 335, 295, 180), "Quick Tips", content["tips"], "tips")
        self._draw_animation(surface, pygame.Rect(745, 185, 420, 330), content["preview_label"])

        draw_text(surface, "Pause becomes available after your first action.", 18, TEXT_MUTED, (955, 535), center=True)

        checkbox_rect = pygame.Rect(420, 585, 24, 24)
        draw_checkbox(surface, checkbox_rect, self.dont_show, "Don't show again")
        self.back_button.draw(surface)
        self.home_button.draw(surface)
        self.play_button.draw(surface)
