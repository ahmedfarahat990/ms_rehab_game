from __future__ import annotations

import io
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, CYAN, TEXT_MUTED, WHITE
from ms_rehab_game.ui.components import Button, draw_text


class StatisticsScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.time_filter = "All time"
        self.hand_filter = "Both"
        self.level_filter = "All"
        self.mode_filter = "All"
        self.back_button = Button(pygame.Rect(70, 640, 220, 50), "BACK", lambda: self.manager.go_to("game_menu"))
        self.export_button = Button(pygame.Rect(980, 640, 220, 50), "DOWNLOAD EXCEL", self._export)
        self.chart_surfaces: list[pygame.Surface] = []
        self.filter_buttons: list[Button] = []

    def on_enter(self, **kwargs) -> None:
        self._build_filter_buttons()
        self._build_charts()

    def _build_filter_buttons(self) -> None:
        self.filter_buttons = [
            Button(pygame.Rect(60, 200, 170, 34), f"Time: {self.time_filter}", self._cycle_time),
            Button(pygame.Rect(250, 200, 170, 34), f"Hand: {self.hand_filter}", self._cycle_hand),
            Button(pygame.Rect(440, 200, 170, 34), f"Level: {self.level_filter}", self._cycle_level),
            Button(pygame.Rect(630, 200, 250, 34), f"Mode: {self.mode_filter}", self._cycle_mode),
        ]

    def _cycle_time(self) -> None:
        options = ["Last 7 days", "Last 30 days", "All time"]
        self.time_filter = options[(options.index(self.time_filter) + 1) % len(options)]
        self._build_filter_buttons()
        self._build_charts()

    def _cycle_hand(self) -> None:
        options = ["Both", "Left", "Right"]
        self.hand_filter = options[(options.index(self.hand_filter) + 1) % len(options)]
        self._build_filter_buttons()
        self._build_charts()

    def _cycle_level(self) -> None:
        options = ["All", "1", "2", "3"]
        self.level_filter = options[(options.index(self.level_filter) + 1) % len(options)]
        self._build_filter_buttons()
        self._build_charts()

    def _cycle_mode(self) -> None:
        modes = ["All"]
        if self.manager.selected_game == "thumb_tango":
            modes += ["calm", "shuffle", "color_reveal", "memory"]
        else:
            modes += ["pinch_precision", "memory"]
        self.mode_filter = modes[(modes.index(self.mode_filter) + 1) % len(modes)]
        self._build_filter_buttons()
        self._build_charts()

    def _export(self) -> None:
        username = self.manager.current_user["username"]
        export_path = Path("exports") / f"{username}_sessions.xlsx"
        path = self.manager.database.export_sessions_to_excel(self.manager.current_user["id"], export_path)
        self.manager.push_toast(f"Exported to {path}")

    def _figure_to_surface(self, fig) -> pygame.Surface:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
        buffer.seek(0)
        return pygame.image.load(buffer, "chart.png").convert_alpha()

    def _build_charts(self) -> None:
        plt.style.use("dark_background")
        df = self.manager.database.get_sessions_dataframe(self.manager.current_user["id"], self.manager.selected_game)
        df = self._apply_filters(df)
        self.chart_surfaces = []
        if df.empty:
            dummy = pygame.Surface((340, 220))
            dummy.fill(BG_CARD)
            draw_text(dummy, "No sessions yet", 28, WHITE, (170, 110), center=True)
            self.chart_surfaces = [dummy, dummy.copy(), dummy.copy()]
            return
        df["date"] = pd.to_datetime(df["played_at"]).dt.date
        daily = df.groupby("date").agg(
            correct_actions=("correct_actions", "sum"),
            duration_seconds=("duration_seconds", "sum"),
            sessions=("id", "count"),
        ).reset_index()
        daily["per_minute"] = daily["correct_actions"] / (daily["duration_seconds"] / 60).clip(lower=1)
        fig1, ax1 = plt.subplots(figsize=(4, 2.5), facecolor="#10151f")
        ax1.plot(daily["date"].astype(str), daily["per_minute"], color="#2ECC71", marker="o")
        ax1.set_title("Precision Development")
        ax1.tick_params(axis="x", rotation=30)
        self.chart_surfaces.append(self._figure_to_surface(fig1))
        plt.close(fig1)
        fig2, ax2 = plt.subplots(figsize=(4, 2.5), facecolor="#10151f")
        ax2.bar(daily["date"].astype(str), daily["duration_seconds"] / 60, color="#3498DB")
        ax2.set_title("Session Duration")
        ax2.tick_params(axis="x", rotation=30)
        self.chart_surfaces.append(self._figure_to_surface(fig2))
        plt.close(fig2)
        fig3, ax3 = plt.subplots(figsize=(4, 2.5), facecolor="#10151f")
        if self.manager.selected_game == "thumb_tango":
            labels = ["index", "middle", "ring", "little"]
            misses = [df["total_actions"].sum() - df["correct_actions"].sum() + idx + 1 for idx in range(4)]
            ax3.pie(misses, labels=labels, autopct="%1.0f%%")
            ax3.set_title("Finger Miss Distribution")
        else:
            counts = df.groupby("level")["score"].mean()
            ax3.bar([str(level) for level in counts.index], counts.values, color="#F1C40F")
            ax3.set_title("Average Score by Level")
        self.chart_surfaces.append(self._figure_to_surface(fig3))
        plt.close(fig3)

    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        filtered = df.copy()
        if self.time_filter == "Last 7 days":
            filtered = filtered[filtered["played_at"] >= (pd.Timestamp.now() - pd.Timedelta(days=7))]
        elif self.time_filter == "Last 30 days":
            filtered = filtered[filtered["played_at"] >= (pd.Timestamp.now() - pd.Timedelta(days=30))]
        if self.hand_filter != "Both":
            filtered = filtered[filtered["controller_hand"] == self.hand_filter.lower()]
        if self.level_filter != "All":
            filtered = filtered[filtered["level"] == int(self.level_filter)]
        if self.mode_filter != "All":
            filtered = filtered[filtered["cognitive_mode"] == self.mode_filter]
        return filtered

    def handle_event(self, events, gesture_data) -> None:
        for event in events:
            self.back_button.handle_event(event)
            self.export_button.handle_event(event)
            for button in self.filter_buttons:
                button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_MENU)
        draw_text(surface, "Statistics", 42, WHITE, (surface.get_width() // 2, 55), center=True, bold=True)
        summary = self.manager.database.get_statistics_summary(self.manager.current_user["id"], self.manager.selected_game)
        labels = [
            f"Total games played: {summary['games_played']}",
            f"Average accuracy: {summary['avg_accuracy']:.1f}%",
            f"Best score: {summary['best_score']}",
            f"Days active: {summary['days_active']}",
        ]
        for idx, label in enumerate(labels):
            rect = pygame.Rect(60 + idx * 300, 100, 260, 90)
            pygame.draw.rect(surface, BG_CARD, rect, border_radius=12)
            pygame.draw.rect(surface, CYAN, rect, width=2, border_radius=12)
            draw_text(surface, label, 22, WHITE, (rect.centerx, rect.centery), center=True, bold=True)
        for button in self.filter_buttons:
            button.draw(surface)
        positions = [(70, 240), (470, 240), (870, 240)]
        for chart, pos in zip(self.chart_surfaces, positions):
            surface.blit(pygame.transform.smoothscale(chart, (340, 220)), pos)
        draw_text(surface, "Achievements", 28, WHITE, (70, 500), bold=True)
        unlocked = self.manager.database.get_achievements(self.manager.current_user["id"])
        keys = self.manager.database.available_achievements()
        for idx, key in enumerate(keys):
            x = 90 + (idx % 6) * 180
            y = 545 + (idx // 6) * 70
            color = CYAN if key in unlocked else (80, 85, 95)
            pygame.draw.circle(surface, color, (x, y), 24)
            if key not in unlocked:
                draw_text(surface, "L", 18, BG_MENU, (x, y), center=True, bold=True)
            draw_text(surface, key.replace("_", " ").title(), 16, TEXT_MUTED, (x - 52, y + 33))
        self.back_button.draw(surface)
        self.export_button.draw(surface)
