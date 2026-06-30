"""Inline mode — @bot <pack_short> [more] to pull icons into any chat."""
from __future__ import annotations

from pyrogram.enums import ParseMode
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent

from core.emoji import fetch_pack
from handlers.util import allowed
from ui.text import single_emoji

HTML = ParseMode.HTML
PAGE = 50  # inline results per offset page


def register(app) -> None:
    @app.on_inline_query()
    async def _inline(client, iq):
        if not allowed(iq.from_user.id if iq.from_user else None):
            await iq.answer(results=[], cache_time=5)
            return

        query = iq.query.strip()
        if not query:
            await iq.answer(
                results=[],
                cache_time=5,
                switch_pm_text="Open prejos \u2192 send a pack name",
                switch_pm_parameter="start",
            )
            return

        short = query.split()[0].strip().rsplit("/", 1)[-1]
        try:
            infos = await fetch_pack(client, short)
        except Exception:  # noqa: BLE001
            await iq.answer(
                results=[],
                cache_time=5,
                switch_pm_text=f"Pack '{short}' not found",
                switch_pm_parameter="start",
            )
            return

        start = int(iq.offset) if iq.offset and iq.offset.isdigit() else 0
        window = infos[start : start + PAGE]
        results = [
            InlineQueryResultArticle(
                title=f"{info.emoji or '?'}  {info.id_str}",
                description=f"pack {info.set_name}" if info.set_name else "tap to send",
                input_message_content=InputTextMessageContent(
                    single_emoji(info),
                    parse_mode=HTML,
                    disable_web_page_preview=True,
                ),
                id=info.id_str,
            )
            for info in window
        ]
        next_offset = str(start + PAGE) if start + PAGE < len(infos) else ""
        await iq.answer(results=results, cache_time=30, next_offset=next_offset)
