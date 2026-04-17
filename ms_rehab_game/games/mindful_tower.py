from __future__ import annotations

import random

import pygame

from ms_rehab_game.games.base_game import RehabGameBase
from ms_rehab_game.settings import BG_CARD, CYAN, GAME_COLORS, TOWER_CONFIG, WHITE
from ms_rehab_game.ui.components import draw_text


class MindfulTowerGame(RehabGameBase):
    def __init__(self, manager) -> None:
        super().__init__(manager, "mindful_tower")
        self.source_blocks: list[dict] = []
        self.markers: list[dict] = []
        self.target_pattern: list[int] = []
        self.placed: dict[int, int] = {}
        self.dragging_block: dict | None = None
        self.was_pinching = False

    def reset_game_state(self) -> None:
        config = TOWER_CONFIG[self.level]
        self.target_pattern = [random.randint(0, len(GAME_COLORS) - 1) for _ in range(config["count"])]
        self.source_blocks = []
        self.placed = {}
        self.dragging_block = None
        self.was_pinching = False
        self.markers = self._build_markers(config)
        for idx, color_index in enumerate(self.target_pattern):
            self.source_blocks.append(
                {
                    "id": idx,
                    "color_index": color_index,
                    "rect": pygame.Rect(80 + (idx % 4) * (config["block"] + 18), 230 + (idx // 4) * (config["block"] + 18), config["block"], config["block"]),
                    "home": (80 + (idx % 4) * (config["block"] + 18), 230 + (idx // 4) * (config["block"] + 18)),
                }
            )

    def _build_markers(self, config: dict) -> list[dict]:
        markers = []
        base_x = 800
        base_y = 520
        for idx in range(config["count"]):
            col = idx % config["cols"]
            row = idx // config["cols"]
            x = base_x + col * (config["block"] + 10)
            y = base_y - row * (config["block"] + 10)
            markers.append({"index": idx, "rect": pygame.Rect(x, y, config["block"], config["block"]), "color_index": self.target_pattern[idx] if idx < len(self.target_pattern) else 0})
        return markers

    def serialize_state(self) -> dict:
        return {
            "source_blocks": [{"id": b["id"], "color_index": b["color_index"], "rect": [b["rect"].x, b["rect"].y, b["rect"].w, b["rect"].h], "home": list(b["home"])} for b in self.source_blocks],
            "placed": self.placed,
            "target_pattern": self.target_pattern,
            "preview_timer": self.preview_timer,
            "correct_actions": self.correct_actions,
            "total_actions": self.total_actions,
            "best_streak": self.best_streak,
            "streak": self.streak,
        }

    def restore_state(self, state: dict) -> None:
        self.target_pattern = state.get("target_pattern", [])
        config = TOWER_CONFIG[self.level]
        self.markers = self._build_markers(config)
        self.source_blocks = []
        for block in state.get("source_blocks", []):
            rect = pygame.Rect(*block["rect"])
            self.source_blocks.append(
                {
                    "id": block["id"],
                    "color_index": block["color_index"],
                    "rect": rect,
                    "home": tuple(block["home"]),
                }
            )
        self.placed = {int(key): value for key, value in state.get("placed", {}).items()}
        self.preview_timer = state.get("preview_timer", 0.0)
        self.correct_actions = state.get("correct_actions", 0)
        self.total_actions = state.get("total_actions", 0)
        self.best_streak = state.get("best_streak", 0)
        self.streak = state.get("streak", 0)

    def update(self, dt, gesture_data) -> None:
        super().update(dt, gesture_data)
        if self.game_over or self.is_paused:
            return
        if self.preview_timer > 0:
            self.preview_timer = max(0.0, self.preview_timer - dt)
        if self.settings["cognitive_mode"] == "memory" and gesture_data.secondary_hand_hint:
            self.trigger_hint(3.0)
        self._handle_drag(gesture_data)
        if len(self.placed) == len(self.markers):
            self.end_game()

    def _handle_drag(self, gesture_data) -> None:
        hand = gesture_data.controlling_hand
        if not hand:
            return
        pinch = hand["pinch"]
        cursor = pinch["position"]
        pinching = pinch["pinching"]
        if pinching and not self.was_pinching and self.dragging_block is None:
            for block in reversed(self.source_blocks):
                if block["id"] in self.placed.values():
                    continue
                if block["rect"].collidepoint(cursor):
                    self.dragging_block = block
                    break
        if pinching and self.dragging_block:
            self.dragging_block["rect"].center = cursor
        if not pinching and self.was_pinching and self.dragging_block:
            self._drop_block(self.dragging_block)
            self.dragging_block = None
        self.was_pinching = pinching

    def _drop_block(self, block: dict) -> None:
        config = TOWER_CONFIG[self.level]
        snap_threshold = config["snap"]
        block_center = block["rect"].center
        best_marker = None
        best_distance = 999999.0
        for marker in self.markers:
            if marker["index"] in self.placed:
                continue
            distance = pygame.Vector2(block_center).distance_to(marker["rect"].center)
            if distance < best_distance:
                best_distance = distance
                best_marker = marker
        if best_marker and best_distance <= snap_threshold and block["color_index"] == best_marker["color_index"]:
            block["rect"].center = best_marker["rect"].center
            self.placed[best_marker["index"]] = block["id"]
            self.add_result(True, best_marker["rect"].center)
        else:
            block["rect"].topleft = block["home"]
            self.add_result(False, block["rect"].center)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_hud(surface, self.manager.gesture_thread.get_latest())
        self.draw_playfield(surface)
        self.particles.draw(surface)
        if self.is_paused:
            self.draw_pause_overlay(surface)
        if self.game_over:
            self.draw_finish_modal(surface)

    def draw_playfield(self, surface: pygame.Surface) -> None:
        config = TOWER_CONFIG[self.level]
        draw_text(surface, f"Blocks: {len(self.placed)}/{len(self.markers)}", 26, WHITE, (30, 130), bold=True)
        source_area = pygame.Rect(40, 180, 360, 380)
        tower_area = pygame.Rect(720, 160, 420, 420)
        pygame.draw.rect(surface, BG_CARD, source_area, border_radius=12)
        pygame.draw.rect(surface, CYAN, source_area, width=2, border_radius=12)
        pygame.draw.rect(surface, BG_CARD, tower_area, border_radius=12)
        pygame.draw.rect(surface, CYAN, tower_area, width=2, border_radius=12)
        draw_text(surface, "Source Blocks", 24, WHITE, (source_area.centerx, source_area.y + 18), center=True, bold=True)
        draw_text(surface, "Build Tower", 24, WHITE, (tower_area.centerx, tower_area.y + 18), center=True, bold=True)
        for marker in self.markers:
            pygame.draw.rect(surface, (90, 90, 90), marker["rect"], width=2, border_radius=6)
        show_target = self.settings["cognitive_mode"] == "pinch_precision" or self.preview_timer > 0 or self.hint_timer > 0
        preview_rect = pygame.Rect(1030, 70, 200, 120)
        pygame.draw.rect(surface, BG_CARD, preview_rect, border_radius=10)
        pygame.draw.rect(surface, CYAN, preview_rect, width=2, border_radius=10)
        draw_text(surface, "Target", 20, WHITE, (preview_rect.centerx, preview_rect.y + 10), center=True, bold=True)
        if show_target:
            scale = max(16, min(32, 90 // max(1, config["rows"])))
            for idx, color_index in enumerate(self.target_pattern):
                col = idx % config["cols"]
                row = idx // config["cols"]
                rect = pygame.Rect(preview_rect.x + 20 + col * (scale + 6), preview_rect.bottom - 20 - (row + 1) * (scale + 6), scale, scale)
                pygame.draw.rect(surface, GAME_COLORS[color_index], rect, border_radius=4)
        elif self.settings["cognitive_mode"] == "memory":
            draw_text(surface, "Memory mode", 18, WHITE, (preview_rect.centerx, preview_rect.centery), center=True)
        for block in self.source_blocks:
            color = GAME_COLORS[block["color_index"]]
            rect = block["rect"]
            pygame.draw.rect(surface, color, rect, border_radius=8)
            pygame.draw.rect(surface, WHITE, rect, width=2, border_radius=8)
        for marker_index, block_id in self.placed.items():
            marker = self.markers[marker_index]
            block = next((item for item in self.source_blocks if item["id"] == block_id), None)
            if block:
                pygame.draw.rect(surface, GAME_COLORS[block["color_index"]], marker["rect"], border_radius=8)
                pygame.draw.rect(surface, WHITE, marker["rect"], width=2, border_radius=8)
