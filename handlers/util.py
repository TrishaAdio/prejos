"""Shared handler helpers: access control, safe sends with graceful fallback."""
from __future__ import annotations

from config import config
from ui.text import has_ce, strip_ce

_username_cache: dict[int, str] = {}


def allowed(user_id: int | None) -> bool:
    if not config.allowed_users:
        return True
    return user_id in config.allowed_users


async def get_username(client) -> str:
    if not _username_cache:
        try:
            me = await client.get_me()
            _username_cache[0] = me.username or ""
        except Exception:  # noqa: BLE001
            _username_cache[0] = ""
    return _username_cache.get(0, "")


async def safe_reply(message, text: str, **kwargs):
    """Reply; if a premium-gated send is rejected, retry without custom emoji."""
    try:
        return await message.reply_text(text, **kwargs)
    except Exception:  # noqa: BLE001
        if has_ce(text):
            return await message.reply_text(strip_ce(text), **kwargs)
        raise


async def safe_edit(message, text: str, **kwargs):
    try:
        return await message.edit_text(text, **kwargs)
    except Exception as exc:  # noqa: BLE001
        if "MESSAGE_NOT_MODIFIED" in str(exc).upper():
            return None
        if has_ce(text):
            try:
                return await message.edit_text(strip_ce(text), **kwargs)
            except Exception:  # noqa: BLE001
                return None
        return None
