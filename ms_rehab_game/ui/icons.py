from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame


ICON_GLYPHS: dict[str, str] = {
    "play": "\uf04b",
    "resume": "\uf04b",
    "back": "\uf060",
    "menu": "\uf0c9",
    "new": "\uf055",
    "stats": "\uf080",
    "settings": "\uf013",
    "login": "\uf084",
    "register": "\uf234",
    "save": "\uf0c7",
    "export": "\uf56e",
    "logout": "\uf2f5",
    "next": "\uf051",
    "replay": "\uf01e",
}


@lru_cache(maxsize=1)
def _fontawesome_path() -> str | None:
    try:
        import fontawesomefree
    except Exception:
        return None

    root = Path(fontawesomefree.__file__).resolve().parent
    candidates = [
        root / "static" / "fontawesomefree" / "webfonts" / "fa-solid-900.ttf",
        root / "webfonts" / "fa-solid-900.ttf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    matches = sorted(root.rglob("fa-solid-900.ttf"))
    return str(matches[0]) if matches else None


@lru_cache(maxsize=32)
def _icon_font(size: int) -> pygame.font.Font | None:
    font_path = _fontawesome_path()
    if not font_path:
        return None
    try:
        return pygame.font.Font(font_path, size)
    except pygame.error:
        return None


def render_icon(icon_name: str, size: int, color: tuple[int, int, int]) -> pygame.Surface | None:
    glyph = ICON_GLYPHS.get(icon_name)
    if not glyph:
        return None
    font = _icon_font(size)
    if font is None:
        return None
    return font.render(glyph, True, color)
