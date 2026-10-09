"""
Emoji icon loader — used across all cogs.
All embeds import `e` from here and use  e("members"),  e("shield"), etc.

If an emoji ID is invalid / not found, it gracefully falls back
to a plain Unicode fallback so embeds never break.
"""

import json
import os

_FALLBACKS: dict[str, str] = {
    "dot_green":     "🟢",  "dot_red":      "🔴",  "dot_orange":    "🟡",  "dot_gray":     "⚫",
    "members":       "👥",  "bot":          "🤖",  "online":        "🟢",  "offline":      "⚫",
    "text_channel":  "💬",  "voice_channel":"🔊",  "category":      "📁",  "thread":       "🧵",
    "id":            "🪪",  "owner":        "👑",  "calendar":      "📅",  "joined":       "📥",
    "role":          "🎭",  "badge":        "🏅",  "boost":         "💎",  "verified":     "✅",
    "followers":     "👥",  "following":    "➡️",  "posts":         "📷",  "private":      "🔒",
    "globe":         "🌐",  "link":         "🔗",
    "latency":       "📡",  "shield":       "🛡️",  "warning":       "⚠️",  "error":        "❌",
    "success":       "✅",  "loading":      "⏳",
    "instagram":     "📸",  "avatar":       "🖼️",  "banner":        "🖼️",  "emoji_icon":   "😄",
    "sticker":       "🔖",
    "ping_great":    "🟩",  "ping_good":    "🟩",  "ping_avg":      "🟨",  "ping_bad":     "🟧",
    "ping_dead":     "🟥",
}

_EMOJIS: dict[str, str] = {}


def _load():
    global _EMOJIS
    path = os.path.join(os.path.dirname(__file__), "emojis.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Strip comment keys
        _EMOJIS = {k: v for k, v in raw.items() if not k.startswith("_")}
    except FileNotFoundError:
        _EMOJIS = {}


_load()


def e(key: str) -> str:
    """Return the custom emoji string for a key, with fallback to Unicode."""
    return _EMOJIS.get(key, _FALLBACKS.get(key, "▪️"))
