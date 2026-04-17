from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any

import bcrypt
import pandas as pd
from openpyxl import Workbook

from ms_rehab_game.settings import ACHIEVEMENT_KEYS, DB_PATH, DEFAULT_USER_GAME_SETTINGS, medal_for_score


class DatabaseManager:
    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS game_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    game_name TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    cognitive_mode TEXT,
                    controller_hand TEXT,
                    score INTEGER NOT NULL,
                    accuracy REAL,
                    duration_seconds INTEGER,
                    correct_actions INTEGER,
                    total_actions INTEGER,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    achievement_key TEXT NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS paused_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    game_name TEXT,
                    level INTEGER,
                    cognitive_mode TEXT,
                    score INTEGER,
                    time_remaining INTEGER,
                    state_json TEXT,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS user_game_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_name TEXT NOT NULL,
                    controller_hand TEXT NOT NULL DEFAULT 'right',
                    duration_minutes INTEGER NOT NULL DEFAULT 3,
                    sound_enabled INTEGER NOT NULL DEFAULT 1,
                    cognitive_mode TEXT NOT NULL DEFAULT 'calm',
                    show_tutorial INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(user_id, game_name)
                );
                """
            )

    def create_user(self, username: str, password: str) -> tuple[bool, str]:
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        try:
            with self.connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username.strip(), password_hash),
                )
                user_id = cursor.lastrowid
            for game_name in ("thumb_tango", "mindful_tower"):
                self.save_user_game_settings(user_id, game_name, DEFAULT_USER_GAME_SETTINGS.copy())
            return True, "Account created successfully."
        except sqlite3.IntegrityError:
            return False, "That username is already in use."

    def authenticate_user(self, username: str, password: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
        if row and bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
            return dict(row)
        return None

    def get_user_game_settings(self, user_id: int, game_name: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_game_settings WHERE user_id = ? AND game_name = ?",
                (user_id, game_name),
            ).fetchone()
        if row:
            return {
                "controller_hand": row["controller_hand"],
                "duration_minutes": row["duration_minutes"],
                "sound_enabled": bool(row["sound_enabled"]),
                "cognitive_mode": row["cognitive_mode"],
                "show_tutorial": bool(row["show_tutorial"]),
            }
        self.save_user_game_settings(user_id, game_name, DEFAULT_USER_GAME_SETTINGS.copy())
        return DEFAULT_USER_GAME_SETTINGS.copy()

    def save_user_game_settings(self, user_id: int, game_name: str, settings: dict[str, Any]) -> None:
        merged = DEFAULT_USER_GAME_SETTINGS.copy()
        merged.update(settings)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_game_settings (
                    user_id, game_name, controller_hand, duration_minutes, sound_enabled, cognitive_mode, show_tutorial
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, game_name) DO UPDATE SET
                    controller_hand=excluded.controller_hand,
                    duration_minutes=excluded.duration_minutes,
                    sound_enabled=excluded.sound_enabled,
                    cognitive_mode=excluded.cognitive_mode,
                    show_tutorial=excluded.show_tutorial
                """,
                (
                    user_id,
                    game_name,
                    merged["controller_hand"],
                    int(merged["duration_minutes"]),
                    1 if merged["sound_enabled"] else 0,
                    merged["cognitive_mode"],
                    1 if merged["show_tutorial"] else 0,
                ),
            )

    def save_paused_session(
        self,
        user_id: int,
        game_name: str,
        level: int,
        cognitive_mode: str,
        score: int,
        time_remaining: int,
        state: dict[str, Any],
    ) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM paused_sessions WHERE user_id = ? AND game_name = ?", (user_id, game_name))
            conn.execute(
                """
                INSERT INTO paused_sessions (
                    user_id, game_name, level, cognitive_mode, score, time_remaining, state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, game_name, level, cognitive_mode, score, time_remaining, json.dumps(state)),
            )

    def get_paused_session(self, user_id: int, game_name: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM paused_sessions WHERE user_id = ? AND game_name = ? ORDER BY saved_at DESC LIMIT 1",
                (user_id, game_name),
            ).fetchone()
        if not row:
            return None
        payload = dict(row)
        payload["state_json"] = json.loads(payload["state_json"]) if payload["state_json"] else {}
        return payload

    def clear_paused_session(self, user_id: int, game_name: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM paused_sessions WHERE user_id = ? AND game_name = ?", (user_id, game_name))

    def save_session(
        self,
        user_id: int,
        game_name: str,
        level: int,
        cognitive_mode: str,
        controller_hand: str,
        score: int,
        accuracy: float,
        duration_seconds: int,
        correct_actions: int,
        total_actions: int,
        meta: dict[str, Any] | None = None,
    ) -> tuple[int, list[str]]:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO game_sessions (
                    user_id, game_name, level, cognitive_mode, controller_hand, score,
                    accuracy, duration_seconds, correct_actions, total_actions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    game_name,
                    level,
                    cognitive_mode,
                    controller_hand,
                    score,
                    accuracy,
                    duration_seconds,
                    correct_actions,
                    total_actions,
                ),
            )
            session_id = cursor.lastrowid
        achievements = self.evaluate_achievements(
            user_id,
            game_name,
            score,
            perfect=total_actions > 0 and correct_actions == total_actions,
            streak=max((meta or {}).get("best_streak", 0), 0),
        )
        self.clear_paused_session(user_id, game_name)
        return session_id, achievements

    def get_sessions_dataframe(self, user_id: int, game_name: str | None = None) -> pd.DataFrame:
        query = "SELECT * FROM game_sessions WHERE user_id = ?"
        params: list[Any] = [user_id]
        if game_name:
            query += " AND game_name = ?"
            params.append(game_name)
        query += " ORDER BY played_at ASC"
        with self.connect() as conn:
            return pd.read_sql_query(query, conn, params=params, parse_dates=["played_at"])

    def get_statistics_summary(self, user_id: int, game_name: str | None = None) -> dict[str, Any]:
        df = self.get_sessions_dataframe(user_id, game_name)
        if df.empty:
            return {"games_played": 0, "avg_accuracy": 0.0, "best_score": 0, "days_active": 0}
        return {
            "games_played": int(len(df)),
            "avg_accuracy": float(df["accuracy"].fillna(0).mean()),
            "best_score": int(df["score"].max()),
            "days_active": int(df["played_at"].dt.date.nunique()),
        }

    def export_sessions_to_excel(self, user_id: int, export_path: str | Path) -> Path:
        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        df = self.get_sessions_dataframe(user_id)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sessions"
        if df.empty:
            sheet.append(["No session data available"])
        else:
            sheet.append(list(df.columns))
            for row in df.itertuples(index=False):
                sheet.append(list(row))
        workbook.save(export_path)
        return export_path

    def get_best_score(self, user_id: int, game_name: str) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(score), 0) AS best_score FROM game_sessions WHERE user_id = ? AND game_name = ?",
                (user_id, game_name),
            ).fetchone()
        return int(row["best_score"]) if row else 0

    def get_achievements(self, user_id: int) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT achievement_key FROM achievements WHERE user_id = ?", (user_id,)).fetchall()
        return {row["achievement_key"] for row in rows}

    def unlock_achievement(self, user_id: int, key: str) -> bool:
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_key = ?",
                (user_id, key),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                "INSERT INTO achievements (user_id, achievement_key) VALUES (?, ?)",
                (user_id, key),
            )
        return True

    def consecutive_days_played(self, user_id: int) -> int:
        df = self.get_sessions_dataframe(user_id)
        if df.empty:
            return 0
        dates = sorted(set(df["played_at"].dt.date))
        streak = 1
        best = 1
        for prev, current in zip(dates, dates[1:]):
            if current == prev + timedelta(days=1):
                streak += 1
                best = max(best, streak)
            elif current != prev:
                streak = 1
        return best

    def evaluate_achievements(self, user_id: int, game_name: str, score: int, perfect: bool, streak: int) -> list[str]:
        unlocked: list[str] = []
        total_sessions = self.get_sessions_dataframe(user_id)
        if len(total_sessions) == 1 and self.unlock_achievement(user_id, "first_game"):
            unlocked.append("first_game")
        medal = medal_for_score(game_name, score).lower()
        if self.unlock_achievement(user_id, medal):
            unlocked.append(medal)
        for threshold in (5, 10, 15):
            key = f"streak_{threshold}"
            if streak >= threshold and self.unlock_achievement(user_id, key):
                unlocked.append(key)
        if perfect and self.unlock_achievement(user_id, "perfect_game"):
            unlocked.append("perfect_game")
        days = self.consecutive_days_played(user_id)
        for threshold in (10, 20, 30):
            key = f"days_{threshold}"
            if days >= threshold and self.unlock_achievement(user_id, key):
                unlocked.append(key)
        return unlocked

    def available_achievements(self) -> list[str]:
        return ACHIEVEMENT_KEYS
