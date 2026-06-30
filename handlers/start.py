"""/start, /help and their navigation callbacks."""
from __future__ import annotations

from pyrogram import filters
from pyrogram.enums import ParseMode

from handlers.util import allowed, get_username, safe_edit, safe_reply
from ui.keyboards import help_kb, start_kb
from ui.text import help_text, start_text

HTML = ParseMode.HTML


def register(app) -> None:
    @app.on_message(filters.command("start") & filters.private)
    async def _start(client, message):
        if not allowed(message.from_user.id):
            return
        await safe_reply(
            message,
            start_text(message.from_user.first_name or "there"),
            reply_markup=start_kb(),
            parse_mode=HTML,
            disable_web_page_preview=True,
        )

    @app.on_message(filters.command("help"))
    async def _help(client, message):
        uid = message.from_user.id if message.from_user else None
        if not allowed(uid):
            return
        await safe_reply(
            message,
            help_text(await get_username(client)),
            reply_markup=help_kb(),
            parse_mode=HTML,
            disable_web_page_preview=True,
        )

    @app.on_callback_query(filters.regex("^start$"))
    async def _cb_start(client, cbq):
        await safe_edit(
            cbq.message,
            start_text(cbq.from_user.first_name or "there"),
            reply_markup=start_kb(),
            parse_mode=HTML,
            disable_web_page_preview=True,
        )
        await cbq.answer()

    @app.on_callback_query(filters.regex("^help$"))
    async def _cb_help(client, cbq):
        await safe_edit(
            cbq.message,
            help_text(await get_username(client)),
            reply_markup=help_kb(),
            parse_mode=HTML,
            disable_web_page_preview=True,
        )
        await cbq.answer()

    @app.on_callback_query(filters.regex("^noop$"))
    async def _noop(client, cbq):
        await cbq.answer()
