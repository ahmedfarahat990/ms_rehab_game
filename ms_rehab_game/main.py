from __future__ import annotations

import sys
from typing import Any

import pygame

from ms_rehab_game.audio import SoundBank
from ms_rehab_game.database import DatabaseManager
from ms_rehab_game.gesture_detector import GestureSnapshot, MediaPipeGestureThread
from ms_rehab_game.settings import BG_MENU, FADE_DURATION, FPS, MIN_HEIGHT, MIN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH, TITLE
from ms_rehab_game.ui.components import ToastManager


class ScreenManager:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.database = DatabaseManager()
        self.gesture_thread = MediaPipeGestureThread()
        self.gesture_thread.start()
        self.sound_bank = SoundBank()
        self.toast_manager = ToastManager()
        self.current_user: dict[str, Any] | None = None
        self.selected_game = "thumb_tango"
        self.selected_level = 1
        self.running = True
        self.fade_alpha = 255
        self.fade_direction = -1
        self.pending_screen: tuple[str, dict[str, Any]] | None = None
        from ms_rehab_game.screens.game_menu_screen import GameMenuScreen
        from ms_rehab_game.screens.level_select_screen import LevelSelectScreen
        from ms_rehab_game.screens.login_screen import LoginScreen
        from ms_rehab_game.screens.pause_screen import PauseScreen
        from ms_rehab_game.screens.settings_screen import SettingsScreen
        from ms_rehab_game.screens.start_screen import StartScreen
        from ms_rehab_game.screens.statistics_screen import StatisticsScreen
        from ms_rehab_game.screens.tutorial_screen import TutorialScreen
        from ms_rehab_game.games.thumb_tango import ThumbTangoGame
        from ms_rehab_game.games.mindful_tower import MindfulTowerGame

        self.screens = {
            "login": LoginScreen(self),
            "start": StartScreen(self),
            "game_menu": GameMenuScreen(self),
            "level_select": LevelSelectScreen(self),
            "settings": SettingsScreen(self),
            "statistics": StatisticsScreen(self),
            "tutorial": TutorialScreen(self),
            "pause": PauseScreen(self),
            "thumb_tango": ThumbTangoGame(self),
            "mindful_tower": MindfulTowerGame(self),
        }
        self.current_screen = self.screens["login"]
        self.current_screen.on_enter()

    def go_to(self, screen_name: str, **kwargs: Any) -> None:
        self.pending_screen = (screen_name, kwargs)
        self.fade_direction = 1

    def _commit_screen_change(self) -> None:
        if not self.pending_screen:
            return
        self.current_screen.on_exit()
        screen_name, kwargs = self.pending_screen
        self.current_screen = self.screens[screen_name]
        self.current_screen.on_enter(**kwargs)
        self.pending_screen = None
        self.fade_direction = -1
        self.fade_alpha = 255

    def logout(self) -> None:
        self.current_user = None
        self.go_to("login")

    def push_toast(self, title: str, color: tuple[int, int, int] = (26, 188, 156)) -> None:
        self.toast_manager.push(title, color)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    width = max(MIN_WIDTH, event.w)
                    height = max(MIN_HEIGHT, event.h)
                    self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            gesture_data: GestureSnapshot = self.gesture_thread.get_latest()
            self.current_screen.handle_event(events, gesture_data)
            self.current_screen.update(dt, gesture_data)
            self.toast_manager.update(dt)
            self.current_screen.draw(self.screen)
            self.toast_manager.draw(self.screen)
            self._draw_fade(dt)
            pygame.display.flip()
        self.shutdown()

    def _draw_fade(self, dt: float) -> None:
        if self.fade_direction == 0:
            return
        self.fade_alpha += int(255 * dt / FADE_DURATION) * self.fade_direction
        self.fade_alpha = max(0, min(255, self.fade_alpha))
        if self.fade_alpha >= 255 and self.pending_screen:
            self._commit_screen_change()
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self.fade_alpha))
        self.screen.blit(overlay, (0, 0))

    def shutdown(self) -> None:
        self.gesture_thread.stop()
        pygame.quit()


def main() -> None:
    manager = ScreenManager()
    manager.run()


if __name__ == "__main__":
    sys.exit(main())
