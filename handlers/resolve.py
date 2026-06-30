"""Resolve premium emoji from any message the bot receives."""
from __future__ import annotations

from pyrogram import filters
from pyrogram.enums import ParseMode

from core.emoji import extract_ids, resolve_ids
from handlers.util import allowed, safe_reply
from ui.text import no_emoji_text, resolved_card

HTML = ParseMode.HTML


def register(app) -> None:
    @app.on_message(filters.private & ~filters.command(["start", "help", "pack", "sheet"]))
    async def _resolve(client, message):
        if not allowed(message.from_user.id if message.from_user else None):
            return

        target = message.reply_to_message or message
        ids = extract_ids(target)
        if not ids and target is not message:
            ids = extract_ids(message)

        if not ids:
            # Only nudge on plain text; ignore stickers/photos/etc silently.
            if message.text or message.caption:
                await safe_reply(message, no_emoji_text(), parse_mode=HTML)
            return

        resolved = await resolve_ids(client, ids)
        await safe_reply(
            message,
            resolved_card(ids, resolved),
            parse_mode=HTML,
            disable_web_page_preview=True,
        )
