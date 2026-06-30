"""/pack <short_name> [page] — browse a whole pack with inline pagination."""
from __future__ import annotations

import time

from pyrogram import filters
from pyrogram.enums import ParseMode

from core.emoji import EmojiInfo, fetch_pack
from handlers.util import allowed, safe_edit, safe_reply
from ui.keyboards import pack_kb
from ui.text import pack_not_found, pack_page

HTML = ParseMode.HTML
PER_PAGE = 12
_TTL = 300  # seconds to cache a fetched pack
_cache: dict[str, tuple[float, list[EmojiInfo]]] = {}


async def _get_pack(client, short: str) -> list[EmojiInfo]:
    hit = _cache.get(short)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    infos = await fetch_pack(client, short)
    _cache[short] = (time.time(), infos)
    return infos


def _render(short: str, infos: list[EmojiInfo], page: int) -> tuple[str, object]:
    pages = max(1, (len(infos) + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, pages))
    window = infos[(page - 1) * PER_PAGE : page * PER_PAGE]
    return pack_page(short, window, page, pages, len(infos)), pack_kb(short, page, pages)


def register(app) -> None:
    @app.on_message(filters.command("pack"))
    async def _pack(client, message):
        if not allowed(message.from_user.id if message.from_user else None):
            return
        parts = message.command[1:]
        if not parts:
            await safe_reply(
                message,
                "Usage  <code>/pack &lt;short_name&gt; [page]</code>\n"
                "<blockquote>The short name is the part after "
                "<code>t.me/addemoji/</code>.</blockquote>",
                parse_mode=HTML,
            )
            return
        short = parts[0].strip().rsplit("/", 1)[-1]
        page = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1

        try:
            infos = await _get_pack(client, short)
        except Exception:  # noqa: BLE001
            await safe_reply(message, pack_not_found(short), parse_mode=HTML)
            return
        if not infos:
            await safe_reply(message, pack_not_found(short), parse_mode=HTML)
            return

        text, kb = _render(short, infos, page)
        await safe_reply(message, text, reply_markup=kb, parse_mode=HTML, disable_web_page_preview=True)

    @app.on_callback_query(filters.regex(r"^pg:"))
    async def _paginate(client, cbq):
        try:
            _, short, page_s = cbq.data.split(":", 2)
            page = int(page_s)
        except (ValueError, AttributeError):
            await cbq.answer()
            return
        try:
            infos = await _get_pack(client, short)
        except Exception:  # noqa: BLE001
            await cbq.answer("Pack unavailable", show_alert=True)
            return
        if not infos:
            await cbq.answer("Pack unavailable", show_alert=True)
            return
        text, kb = _render(short, infos, page)
        await safe_edit(cbq.message, text, reply_markup=kb, parse_mode=HTML, disable_web_page_preview=True)
        await cbq.answer()
