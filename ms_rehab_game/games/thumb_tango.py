from __future__ import annotations

import random

import pygame

from ms_rehab_game.games.base_game import RehabGameBase
from ms_rehab_game.settings import BG_CARD, CYAN, DARK_GRAY, GRAY, LANE_TO_COLOR, LANE_TO_NAME, RED, TEXT_MUTED, THUMB_SPEEDS, WHITE
from ms_rehab_game.ui.components import draw_text


class ThumbTangoGame(RehabGameBase):
    def __init__(self, manager) -> None:
        super().__init__(manager, "thumb_tango")
        self.balls: list[dict] = []
        self.spawn_timer = 0.0
        self.flash_timer = [0.0] * 4
        self.flash_color = [CYAN] * 4
        self.box_order = [1, 2, 3, 4]
        self.shuffle_timer = 10.0
        self.memory_visible = True
        self.gesture_cooldown = 0.0

    def reset_game_state(self) -> None:
        self.balls = []
        self.spawn_timer = 0.4
        self.flash_timer = [0.0] * 4
        self.flash_color = [CYAN] * 4
        self.box_order = [1, 2, 3, 4]
        self.shuffle_timer = 10.0
        self.memory_visible = True
        self.gesture_cooldown = 0.0

    def serialize_state(self) -> dict:
        return {
            "balls": self.balls,
            "flash_timer": self.flash_timer,
            "flash_color": self.flash_color,
            "box_order": self.box_order,
            "shuffle_timer": self.shuffle_timer,
            "memory_visible": self.memory_visible,
            "gesture_cooldown": self.gesture_cooldown,
            "correct_actions": self.correct_actions,
            "total_actions": self.total_actions,
            "best_streak": self.best_streak,
            "streak": self.streak,
            "preview_timer": self.preview_timer,
        }

    def restore_state(self, state: dict) -> None:
        self.balls = state.get("balls", [])
        self.flash_timer = state.get("flash_timer", [0.0] * 4)
        self.flash_color = state.get("flash_color", [CYAN] * 4)
        self.box_order = state.get("box_order", [1, 2, 3, 4])
        self.shuffle_timer = state.get("shuffle_timer", 10.0)
        self.memory_visible = state.get("memory_visible", True)
        self.gesture_cooldown = state.get("gesture_cooldown", 0.0)
        self.correct_actions = state.get("correct_actions", 0)
        self.total_actions = state.get("total_actions", 0)
        self.best_streak = state.get("best_streak", 0)
        self.streak = state.get("streak", 0)
        self.preview_timer = state.get("preview_timer", 0.0)

    def update(self, dt, gesture_data) -> None:
        # Track hand cursor position so HUD buttons are pinch-operable
        hand = gesture_data.controlling_hand
        if hand:
            self.hand_cursor_pos     = self._map_cursor_to_screen(hand["pinch"]["position"])
            self.hand_cursor_pinching = hand["pinch"]["pinching"]
        else:
            self.hand_cursor_pos     = None
            self.hand_cursor_pinching = False
        super().update(dt, gesture_data)
        if self.game_over or self.is_paused:
            return
        self.spawn_timer -= dt
        self.shuffle_timer -= dt
        self.gesture_cooldown = max(0.0, self.gesture_cooldown - dt)
        if self.preview_timer > 0:
            self.preview_timer = max(0.0, self.preview_timer - dt)
            if self.preview_timer == 0 and self.settings["cognitive_mode"] == "memory":
                self.memory_visible = False
        if gesture_data.secondary_hand_hint and self.settings["cognitive_mode"] == "memory":
            self.trigger_hint(2.0)
        if self.settings["cognitive_mode"] == "shuffle" and self.shuffle_timer <= 0:
            random.shuffle(self.box_order)
            self.shuffle_timer = 10.0
        if self.spawn_timer <= 0:
            self.spawn_ball()
            self.spawn_timer = max(0.7, 1.7 - self.level * 0.25)
        self.move_balls(dt)
        self.process_gesture(gesture_data)
        self.update_flashes(dt)

    def spawn_ball(self) -> None:
        color_lane = random.randint(1, 4)
        ball = {"x": 640.0, "y": -25.0, "color_lane": color_lane, "display_lane": color_lane, "revealed": self.settings["cognitive_mode"] != "color_reveal"}
        self.balls.append(ball)

    def move_balls(self, dt: float) -> None:
        speed = THUMB_SPEEDS[self.level]
        survivors = []
        for ball in self.balls:
            ball["y"] += speed * dt
            split_zone_y = 340
            if self.settings["cognitive_mode"] == "color_reveal" and ball["y"] > split_zone_y - speed:
                ball["revealed"] = True
            if not ball["revealed"]:
                ball["display_lane"] = int((pygame.time.get_ticks() // 120) % 4) + 1
            if ball["y"] > 620:
                self.add_result(False, (ball["x"], 590))
                self.flash_lane(self.box_order.index(ball["color_lane"]) + 1, RED)
                continue
            survivors.append(ball)
        self.balls = survivors

    def process_gesture(self, gesture_data) -> None:
        if self.gesture_cooldown > 0 or not gesture_data.controlling_hand:
            return
        # Don't register thumb gestures while a confirm dialog is showing
        if self._confirming:
            return
        opposition = gesture_data.controlling_hand["opposition"]
        if not opposition["active"]:
            return
        active_ball = next((ball for ball in self.balls if 320 <= ball["y"] <= 490), None)
        if not active_ball:
            return
        target_lane_position = self.box_order.index(active_ball["color_lane"]) + 1
        success = opposition["lane"] == target_lane_position
        self.add_result(success, (active_ball["x"], active_ball["y"]), opposition["finger"])
        self.flash_lane(opposition["lane"], CYAN if success else RED)
        self.balls.remove(active_ball)
        self.gesture_cooldown = 0.35

    def flash_lane(self, lane: int, color) -> None:
        self.flash_timer[lane - 1] = 0.3
        self.flash_color[lane - 1] = color

    def update_flashes(self, dt: float) -> None:
        self.flash_timer = [max(0.0, timer - dt) for timer in self.flash_timer]

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_hud(surface, self.manager.gesture_thread.get_latest())
        self.draw_board(surface)
        self.particles.draw(surface)
        if self.is_paused:
            self.draw_pause_overlay(surface)
        if self.game_over:
            self.draw_finish_modal(surface)
        # Confirm dialog sits above everything except the hand cursor
        self.draw_confirm_overlay(surface)
        if self.hand_cursor_pos:
            self._draw_hand_cursor(surface, self.hand_cursor_pos, self.hand_cursor_pinching)

    def draw_board(self, surface: pygame.Surface) -> None:
        draw_text(surface, "When the ball reaches the split zone, use one thumb-to-finger touch to choose the matching lane.", 22, TEXT_MUTED, (300, 120))
        pygame.draw.line(surface, GRAY, (640, 150), (640, 330), 8)
        split_y = 330
        lane_centers = [350, 520, 760, 930]
        for center in lane_centers:
            pygame.draw.line(surface, GRAY, (640, split_y), (center, 560), 4)
        mode = self.settings["cognitive_mode"]
        show_colors = mode != "memory" or self.memory_visible or self.hint_timer > 0
        for idx, center in enumerate(lane_centers, start=1):
            lane_color_key = self.box_order[idx - 1]
            base_color = LANE_TO_COLOR[lane_color_key] if show_colors else DARK_GRAY
            color = self.flash_color[idx - 1] if self.flash_timer[idx - 1] > 0 else base_color
            rect = pygame.Rect(center - 55, 560, 110, 80)
            pygame.draw.rect(surface, color, rect, border_radius=12)
            pygame.draw.rect(surface, WHITE, rect, width=2, border_radius=12)
            draw_text(surface, LANE_TO_NAME[idx].title(), 18, WHITE, (rect.centerx, rect.bottom + 8), center=True)
        for ball in self.balls:
            color = LANE_TO_COLOR[ball["display_lane"]]
            pygame.draw.circle(surface, color, (int(ball["x"]), int(ball["y"])), 22)
            pygame.draw.circle(surface, WHITE, (int(ball["x"]), int(ball["y"])), 22, 2)
        if mode == "memory" and self.preview_timer > 0:
            draw_text(surface, f"Memorize lane colors: {self.preview_timer:.1f}s", 24, CYAN, (440, 150))

