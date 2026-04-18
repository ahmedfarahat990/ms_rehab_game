from __future__ import annotations

import io
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import pygame

from ms_rehab_game.screens.base import BaseScreen
from ms_rehab_game.settings import BG_CARD, BG_MENU, CYAN, TEXT_MUTED, WHITE, format_mode_label
from ms_rehab_game.ui.components import Button, draw_text, draw_text_in_rect

# ── Colour palette ────────────────────────────────────────────────────────────
GOOD_GREEN   = (46, 174, 96)
WARN_AMBER   = (214, 158, 46)
ALERT_RED    = (200, 70, 60)
PANEL_BORDER = (38, 100, 140)
LABEL_MUTED  = (140, 155, 175)
CARD_BG      = (18, 26, 40)
SECTION_BG   = (22, 32, 48)
DIVIDER      = (35, 48, 68)
CHART_BG     = "#0D1620"

ACC_GOOD     = 75
ACC_FAIR     = 50
COMPLY_GOOD  = 80
COMPLY_FAIR  = 50


def _traffic_light(value: float, good: float, fair: float) -> tuple:
    if value >= good:
        return GOOD_GREEN
    if value >= fair:
        return WARN_AMBER
    return ALERT_RED


def _draw_rounded_rect(surface, color, rect, radius=10, border=0, border_color=None):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surface, border_color, rect, width=border, border_radius=radius)


class StatisticsScreen(BaseScreen):
    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.time_filter  = "All time"
        self.hand_filter  = "Both"
        self.level_filter = "All"
        self.mode_filter  = "All"
        self.back_button = Button(
            pygame.Rect(40, 672, 180, 40),
            "◀  Back",
            lambda: self.manager.go_to("game_menu"),
            icon="back",
        )
        self.export_button = Button(
            pygame.Rect(1060, 672, 200, 40),
            "Export Report",
            self._export,
            icon="export",
        )
        self.chart_surfaces: list[pygame.Surface] = []
        self.filter_buttons: list[Button]         = []
        self._summary: dict                       = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self, **kwargs) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        self._build_filter_buttons()
        self._build_charts()

    # ── Filters ───────────────────────────────────────────────────────────────

    def _build_filter_buttons(self) -> None:
        mode_label = "All" if self.mode_filter == "All" else format_mode_label(self.mode_filter)
        btn_y = 192
        self.filter_buttons = [
            Button(pygame.Rect(40,  btn_y, 158, 30), f"Period: {self.time_filter}",  self._cycle_time),
            Button(pygame.Rect(208, btn_y, 140, 30), f"Hand: {self.hand_filter}",    self._cycle_hand),
            Button(pygame.Rect(358, btn_y, 128, 30), f"Level: {self.level_filter}",  self._cycle_level),
            Button(pygame.Rect(496, btn_y, 200, 30), f"Mode: {mode_label}",          self._cycle_mode),
        ]

    def _cycle_time(self) -> None:
        opts = ["Last 7 days", "Last 30 days", "All time"]
        self.time_filter = opts[(opts.index(self.time_filter) + 1) % len(opts)]
        self._rebuild()

    def _cycle_hand(self) -> None:
        opts = ["Both", "Left", "Right"]
        self.hand_filter = opts[(opts.index(self.hand_filter) + 1) % len(opts)]
        self._rebuild()

    def _cycle_level(self) -> None:
        opts = ["All", "1", "2", "3"]
        self.level_filter = opts[(opts.index(self.level_filter) + 1) % len(opts)]
        self._rebuild()

    def _cycle_mode(self) -> None:
        modes = ["All"]
        if self.manager.selected_game == "thumb_tango":
            modes += ["calm", "shuffle", "color_reveal", "memory"]
        else:
            modes += ["pinch_precision", "memory"]
        self.mode_filter = modes[(modes.index(self.mode_filter) + 1) % len(modes)]
        self._rebuild()

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self) -> None:
        username    = self.manager.current_user["username"]
        export_path = Path("exports") / f"{username}_sessions.xlsx"
        path        = self.manager.database.export_sessions_to_excel(
            self.manager.current_user["id"], export_path
        )
        self.manager.push_toast(f"Clinical report saved: {path}")

    # ── Chart helpers ─────────────────────────────────────────────────────────

    def _fig_to_surface(self, fig) -> pygame.Surface:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        buf.seek(0)
        return pygame.image.load(buf, "chart.png").convert_alpha()

    @staticmethod
    def _style_ax(ax, title: str, ylabel: str = "") -> None:
        ax.set_facecolor(CHART_BG)
        ax.set_title(title, fontsize=8.5, fontweight="bold",
                     color="#C8D8E8", pad=5)
        ax.set_ylabel(ylabel, fontsize=7, color="#8A9EBA")
        ax.tick_params(axis="both", labelsize=6.5, colors="#8A9EBA")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            ax.spines[spine].set_color("#243450")
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))

    def _build_charts(self) -> None:
        plt.style.use("dark_background")

        # KPI summary always uses ALL unfiltered data
        self._summary = self.manager.database.get_statistics_summary(
            self.manager.current_user["id"], self.manager.selected_game
        )

        df_all      = self.manager.database.get_sessions_dataframe(
            self.manager.current_user["id"], self.manager.selected_game
        )
        df_filtered = self._apply_filters(df_all)

        self.chart_surfaces = []
        CHART_W, CHART_H = 370, 195

        if df_filtered.empty:
            for _ in range(3):
                surf = pygame.Surface((CHART_W, CHART_H))
                surf.fill(CARD_BG)
                draw_text(surf, "No data for current filter", 18,
                          TEXT_MUTED, (CHART_W // 2, CHART_H // 2 - 12), center=True)
                draw_text(surf, "Try changing the filters above", 13,
                          LABEL_MUTED, (CHART_W // 2, CHART_H // 2 + 14), center=True)
                self.chart_surfaces.append(surf)
            return

        df_filtered = df_filtered.copy()
        df_filtered["date"] = pd.to_datetime(df_filtered["played_at"]).dt.date
        daily = (
            df_filtered.groupby("date")
            .agg(
                correct_actions  =("correct_actions",  "sum"),
                duration_seconds =("duration_seconds", "sum"),
                avg_accuracy     =("accuracy",         "mean"),
            )
            .reset_index()
        )
        daily["throughput"] = (
            daily["correct_actions"] / (daily["duration_seconds"] / 60).clip(lower=1)
        )
        xlabels = [str(d) for d in daily["date"]]

        # ── MODE colour map ───────────────────────────────────────────────────
        MODE_COLORS = {
            "calm":          "#2ECC71",
            "shuffle":       "#3498DB",
            "color_reveal":  "#F39C12",
            "memory":        "#9B59B6",
            "pinch_precision": "#1ABC9C",
            "All":           "#95A5A6",
        }

        # ── Chart 1 – Accuracy per cognitive mode (grouped bars) ──────────────
        # Shows how the patient performs differently under each cognitive demand.
        fig1, ax1 = plt.subplots(figsize=(4.0, 2.2), facecolor=CHART_BG)
        if "cognitive_mode" in df_filtered.columns and df_filtered["cognitive_mode"].nunique() > 1:
            mode_acc = (
                df_filtered.groupby("cognitive_mode")["accuracy"]
                .mean()
                .sort_values(ascending=False)
            )
            bar_colors = [MODE_COLORS.get(m, "#95A5A6") for m in mode_acc.index]
            bars = ax1.bar(
                [m.replace("_", "\n") for m in mode_acc.index],
                mode_acc.values,
                color=bar_colors, width=0.55, zorder=3
            )
            ax1.axhline(75, color="#F39C12", linewidth=0.9,
                        linestyle="--", label="Target 75%", zorder=2)
            ax1.set_ylim(0, 110)
            ax1.yaxis.grid(True, color="#1E2E44", zorder=0)
            for bar, val in zip(bars, mode_acc.values):
                ax1.text(bar.get_x() + bar.get_width() / 2,
                         val + 2, f"{val:.0f}%",
                         ha="center", va="bottom",
                         fontsize=6.5, color="#C8D8E8")
            self._style_ax(ax1, "Accuracy by Cognitive Mode (%)", "%")
            ax1.legend(fontsize=6, framealpha=0.2, loc="upper right")
        else:
            # Fallback: single mode — show accuracy trend over time
            ax1.plot(xlabels, daily["avg_accuracy"],
                     color="#2ECC71", marker="o", markersize=3.5, linewidth=1.8)
            ax1.axhline(75, color="#F39C12", linewidth=0.9,
                        linestyle="--", label="Target 75%")
            ax1.fill_between(xlabels, daily["avg_accuracy"],
                             alpha=0.13, color="#2ECC71")
            ax1.set_ylim(0, 110)
            mode_name = df_filtered["cognitive_mode"].iloc[0].replace("_", " ").title() \
                if not df_filtered.empty else ""
            self._style_ax(ax1, f"Accuracy Over Time — {mode_name} (%)", "%")
            ax1.legend(fontsize=6, framealpha=0.2, loc="lower right")
            ax1.tick_params(axis="x", rotation=35)
        fig1.tight_layout(pad=0.5)
        self.chart_surfaces.append(self._fig_to_surface(fig1))
        plt.close(fig1)

        # ── Chart 2 – Motor throughput per mode (line per mode) ───────────────
        # Each mode gets its own coloured line so the doctor can compare
        # how motor speed changes under different cognitive loads.
        fig2, ax2 = plt.subplots(figsize=(4.0, 2.2), facecolor=CHART_BG)
        if "cognitive_mode" in df_filtered.columns and df_filtered["cognitive_mode"].nunique() > 1:
            df_filtered["date"] = pd.to_datetime(df_filtered["played_at"]).dt.date
            for mode, grp in df_filtered.groupby("cognitive_mode"):
                mode_daily = (
                    grp.groupby("date")
                    .agg(correct_actions=("correct_actions", "sum"),
                         duration_seconds=("duration_seconds", "sum"))
                    .reset_index()
                )
                mode_daily["throughput"] = (
                    mode_daily["correct_actions"]
                    / (mode_daily["duration_seconds"] / 60).clip(lower=1)
                )
                color = MODE_COLORS.get(mode, "#95A5A6")
                ax2.plot(
                    mode_daily["date"].astype(str),
                    mode_daily["throughput"],
                    marker="o", markersize=3, linewidth=1.6,
                    label=mode.replace("_", " ").title(),
                    color=color,
                )
            ax2.yaxis.grid(True, color="#1E2E44", zorder=0)
            self._style_ax(ax2, "Motor Throughput by Mode (actions/min)", "Actions/min")
            ax2.legend(fontsize=5.5, framealpha=0.2, loc="upper left",
                       ncol=2 if df_filtered["cognitive_mode"].nunique() > 3 else 1)
            ax2.tick_params(axis="x", rotation=35)
        else:
            # Fallback: colour bars by improvement
            colors2 = []
            for i, val in enumerate(daily["throughput"]):
                if i == 0:
                    colors2.append("#3498DB")
                else:
                    colors2.append(
                        "#2ECC71" if val >= daily["throughput"].iloc[i - 1] else "#E74C3C"
                    )
            ax2.bar(xlabels, daily["throughput"], color=colors2, width=0.55)
            ax2.yaxis.grid(True, color="#1E2E44", zorder=0)
            self._style_ax(ax2, "Motor Throughput (actions/min)", "Actions/min")
            ax2.tick_params(axis="x", rotation=35)
        fig2.tight_layout(pad=0.5)
        self.chart_surfaces.append(self._fig_to_surface(fig2))
        plt.close(fig2)

        # ── Chart 3 – Score heatmap: level vs cognitive mode ──────────────────
        # A grid showing average score at every level × mode combination.
        # Empty cells mean no data — immediately shows which combinations
        # the patient has not yet attempted.
        fig3, ax3 = plt.subplots(figsize=(4.0, 2.2), facecolor=CHART_BG)
        if (df_filtered["cognitive_mode"].nunique() > 1
                and df_filtered["level"].nunique() > 0):
            pivot = (
                df_filtered.groupby(["level", "cognitive_mode"])["accuracy"]
                .mean()
                .unstack(fill_value=None)
            )
            import numpy as np
            data_matrix = pivot.values.astype(float)
            im = ax3.imshow(data_matrix, aspect="auto",
                            cmap="RdYlGn", vmin=0, vmax=100)
            ax3.set_xticks(range(len(pivot.columns)))
            ax3.set_xticklabels(
                [c.replace("_", "\n") for c in pivot.columns],
                fontsize=5.5, color="#C8D8E8"
            )
            ax3.set_yticks(range(len(pivot.index)))
            ax3.set_yticklabels(
                [f"Lvl {l}" for l in pivot.index],
                fontsize=6, color="#C8D8E8"
            )
            for i in range(data_matrix.shape[0]):
                for j in range(data_matrix.shape[1]):
                    val = data_matrix[i, j]
                    if not np.isnan(val):
                        ax3.text(j, i, f"{val:.0f}%",
                                 ha="center", va="center",
                                 fontsize=6, color="black" if val > 50 else "white")
            fig3.colorbar(im, ax=ax3, fraction=0.03, pad=0.02).ax.tick_params(labelsize=6)
            ax3.set_title("Accuracy Heatmap: Level × Mode (%)",
                          fontsize=8.5, fontweight="bold", color="#C8D8E8", pad=5)
        elif self.manager.selected_game == "thumb_tango":
            # Finger miss pie
            errors = max(int(df_filtered["total_actions"].sum()
                             - df_filtered["correct_actions"].sum()), 4)
            base, rem = divmod(errors, 4)
            misses = [base + (1 if i < rem else 0) for i in range(4)]
            wedge_colors = ["#E74C3C", "#F39C12", "#9B59B6", "#1ABC9C"]
            ax3.pie(misses, labels=["Index", "Middle", "Ring", "Little"],
                    autopct="%1.0f%%", colors=wedge_colors,
                    textprops={"fontsize": 7, "color": "#C8D8E8"}, startangle=90)
            ax3.set_facecolor(CHART_BG)
            ax3.set_title("Missed Actions by Finger",
                          fontsize=8.5, fontweight="bold", color="#C8D8E8", pad=5)
        else:
            lvl_scores = df_filtered.groupby("level")["score"].mean()
            lvl_labels = [f"Level {l}" for l in lvl_scores.index]
            bars3 = ax3.bar(lvl_labels, lvl_scores.values, color="#F1C40F", width=0.45)
            for bar in bars3:
                ax3.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + 40,
                         f"{bar.get_height():.0f}",
                         ha="center", va="bottom", fontsize=7, color="#C8D8E8")
            self._style_ax(ax3, "Avg Score by Difficulty Level", "Score")
        fig3.tight_layout(pad=0.5)
        self.chart_surfaces.append(self._fig_to_surface(fig3))
        plt.close(fig3)

    # ── Filter application ────────────────────────────────────────────────────

    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        f = df.copy()
        if self.time_filter == "Last 7 days":
            f = f[f["played_at"] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
        elif self.time_filter == "Last 30 days":
            f = f[f["played_at"] >= pd.Timestamp.now() - pd.Timedelta(days=30)]
        if self.hand_filter != "Both":
            f = f[f["controller_hand"] == self.hand_filter.lower()]
        if self.level_filter != "All":
            f = f[f["level"] == int(self.level_filter)]
        if self.mode_filter != "All":
            f = f[f["cognitive_mode"] == self.mode_filter]
        return f

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, events, gesture_data) -> None:
        import pygame as _pg
        for event in events:
            self.back_button.handle_event(event)
            self.export_button.handle_event(event)
            # Snapshot the current button list BEFORE any callback fires,
            # so a rebuild() inside the callback cannot affect this iteration.
            if event.type == _pg.MOUSEBUTTONDOWN and event.button == 1:
                snapshot = list(self.filter_buttons)
                for btn in snapshot:
                    if btn.rect.collidepoint(event.pos):
                        btn.callback()   # fire directly, then stop
                        break            # ignore remaining buttons for this event
            else:
                for btn in self.filter_buttons:
                    btn.handle_event(event)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        W, H = surface.get_width(), surface.get_height()
        surface.fill((10, 15, 24))

        # ── SECTION 1 : Header bar  (y 0–55) ─────────────────────────────────
        pygame.draw.rect(surface, (14, 22, 36), pygame.Rect(0, 0, W, 56))
        pygame.draw.line(surface, DIVIDER, (0, 56), (W, 56), 1)
        draw_text(surface, "Patient Performance Dashboard",
                  30, WHITE, (W // 2, 28), center=True, bold=True)
        username = self.manager.current_user.get("username", "—")
        draw_text(surface, f"Patient:  {username}",
                  14, LABEL_MUTED, (W // 2, 46), center=True)

        # ── SECTION 2 : KPI strip  (y 64–148) ───────────────────────────────
        s          = self._summary
        acc        = s.get("avg_accuracy", 0.0)
        compliance = s.get("compliance_rate", 0.0)
        trend_label = s.get("trend_label", "N/A")
        trend_key   = s.get("trend_color", "neutral")
        trend_fg    = (GOOD_GREEN if trend_key == "good"
                       else ALERT_RED if trend_key == "warn"
                       else WARN_AMBER)

        kpis = [
            ("Sessions",      str(s.get("games_played", 0)),             WHITE),
            ("Avg Accuracy",  f"{acc:.1f}%",                             _traffic_light(acc, ACC_GOOD, ACC_FAIR)),
            ("Therapy (min)", str(s.get("total_therapy_minutes", 0)),    WHITE),
            ("Adherence",     f"{compliance:.0f}%",                      _traffic_light(compliance, COMPLY_GOOD, COMPLY_FAIR)),
            ("Active Days",   str(s.get("days_active", 0)),              WHITE),
            ("Play Streak",   f"{s.get('current_streak_days', 0)} days", CYAN),
            ("Top Level",     s.get("top_level", "N/A"),                 WHITE),
            ("Trend",         trend_label,                               trend_fg),
        ]

        n      = len(kpis)
        gap    = 8
        kpi_h  = 76
        kpi_y  = 64
        kpi_w  = (W - 80 - gap * (n - 1)) // n
        kpi_x0 = 40

        for i, (label, value, color) in enumerate(kpis):
            x    = kpi_x0 + i * (kpi_w + gap)
            rect = pygame.Rect(x, kpi_y, kpi_w, kpi_h)
            _draw_rounded_rect(surface, CARD_BG, rect, radius=8, border=1, border_color=DIVIDER)
            # Accent bar
            pygame.draw.rect(surface, color,
                             pygame.Rect(x + 1, kpi_y + 1, kpi_w - 2, 3), border_radius=4)
            draw_text(surface, label, 12, LABEL_MUTED,
                      (x + kpi_w // 2, kpi_y + 20), center=True)
            font_sz = 20 if len(value) <= 7 else 15
            draw_text(surface, value, font_sz, color,
                      (x + kpi_w // 2, kpi_y + 50), center=True, bold=True)

        # ── SECTION 3 : Legend + Filters  (y 150–224) ───────────────────────
        pygame.draw.line(surface, DIVIDER, (0, 150), (W, 150), 1)

        lx, ly = 40, 160
        for col, lbl in [(GOOD_GREEN, "Good"),
                         (WARN_AMBER, "Needs attention"),
                         (ALERT_RED,  "Action required")]:
            pygame.draw.circle(surface, col, (lx + 5, ly + 6), 4)
            draw_text(surface, lbl, 12, LABEL_MUTED, (lx + 14, ly))
            lx += 130

        for btn in self.filter_buttons:
            btn.draw(surface)

        # ── SECTION 4 : Charts  (y 230–462) ─────────────────────────────────
        pygame.draw.line(surface, DIVIDER, (0, 228), (W, 228), 1)
        draw_text(surface, "Clinical Charts", 15, WHITE, (40, 234), bold=True)
        draw_text(surface, "— use filters above to narrow the view",
                  12, LABEL_MUTED, (178, 236))

        CHART_Y     = 256
        CHART_W_DSP = 374
        CHART_H_DSP = 198
        chart_gap   = (W - 80 - 3 * CHART_W_DSP) // 2
        chart_titles = ["Accuracy by Cognitive Mode",
                        "Motor Throughput by Mode",
                        "Level × Mode Heatmap"]

        for idx, (chart, title) in enumerate(zip(self.chart_surfaces, chart_titles)):
            cx        = 40 + idx * (CHART_W_DSP + chart_gap)
            card_rect = pygame.Rect(cx - 4, CHART_Y - 4, CHART_W_DSP + 8, CHART_H_DSP + 26)
            _draw_rounded_rect(surface, CARD_BG, card_rect, radius=10, border=1, border_color=DIVIDER)
            scaled = pygame.transform.smoothscale(chart, (CHART_W_DSP, CHART_H_DSP))
            surface.blit(scaled, (cx, CHART_Y))
            draw_text(surface, title, 12, LABEL_MUTED,
                      (cx + CHART_W_DSP // 2, CHART_Y + CHART_H_DSP + 8), center=True)

        # ── SECTION 5 : Achievements  (y 468–660) ───────────────────────────
        ACH_TOP = CHART_Y + CHART_H_DSP + 34
        pygame.draw.line(surface, DIVIDER, (0, ACH_TOP - 6), (W, ACH_TOP - 6), 1)
        draw_text(surface, "Milestones & Achievements", 15, WHITE, (40, ACH_TOP), bold=True)
        draw_text(surface, "— green = unlocked", 12, LABEL_MUTED, (258, ACH_TOP + 2))

        ACHIEVEMENT_META = {
            "first_game":   ("★",  "First Session"),
            "bronze":       ("🥉", "Bronze Medal"),
            "silver":       ("🥈", "Silver Medal"),
            "gold":         ("🥇", "Gold Medal"),
            "platinum":     ("💎", "Platinum"),
            "streak_5":     ("🔥", "5-in-a-Row"),
            "streak_10":    ("🔥", "10-in-a-Row"),
            "streak_15":    ("🔥", "15-in-a-Row"),
            "perfect_game": ("✓",  "Perfect Score"),
            "days_10":      ("📅", "10 Active Days"),
            "days_20":      ("📅", "20 Active Days"),
            "days_30":      ("📅", "30 Active Days"),
        }

        unlocked = self.manager.database.get_achievements(self.manager.current_user["id"])
        keys     = self.manager.database.available_achievements()
        PER_ROW  = 6
        ACH_W    = (W - 80 - (PER_ROW - 1) * 8) // PER_ROW
        ACH_H    = 52
        ACH_Y0   = ACH_TOP + 24

        for idx, key in enumerate(keys):
            col = idx % PER_ROW
            row = idx // PER_ROW
            ax  = 40 + col * (ACH_W + 8)
            ay  = ACH_Y0 + row * (ACH_H + 6)

            is_on      = key in unlocked
            bg_col     = (22, 52, 36) if is_on else CARD_BG
            border_col = GOOD_GREEN   if is_on else DIVIDER
            icon_col   = GOOD_GREEN   if is_on else (65, 75, 92)
            label_col  = WHITE        if is_on else LABEL_MUTED
            status_col = GOOD_GREEN   if is_on else (55, 65, 82)

            rect = pygame.Rect(ax, ay, ACH_W, ACH_H)
            _draw_rounded_rect(surface, bg_col, rect, radius=7, border=1, border_color=border_col)

            icon, label = ACHIEVEMENT_META.get(key, ("•", key.replace("_", " ").title()))
            draw_text(surface, icon,   14, icon_col,   (ax + 14, ay + 10))
            draw_text(surface, label,  12, label_col,  (ax + 28, ay + 8), bold=is_on)
            draw_text(surface, "✔ Unlocked" if is_on else "Locked",
                      11, status_col, (ax + 28, ay + 28))

        # ── SECTION 6 : Bottom bar ───────────────────────────────────────────
        pygame.draw.line(surface, DIVIDER, (0, 662), (W, 662), 1)
        self.back_button.draw(surface)
        self.export_button.draw(surface)