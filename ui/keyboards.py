"""Inline keyboards."""
from __future__ import annotations

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

REPO_URL = "https://github.com/TrishaAdio/prejos"


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("\u2726 Try inline", switch_inline_query_current_chat=""),
                InlineKeyboardButton("\u2754 Help", callback_data="help"),
            ],
            [InlineKeyboardButton("\u2b50 Source", url=REPO_URL)],
        ]
    )


def help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("\u2190 Back", callback_data="start")]]
    )


def pack_kb(short: str, page: int, pages: int) -> InlineKeyboardMarkup:
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton("\u2190 Prev", callback_data=f"pg:{short}:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page}/{pages}", callback_data="noop"))
    if page < pages:
        nav.append(InlineKeyboardButton("Next \u2192", callback_data=f"pg:{short}:{page + 1}"))
    rows = [nav, [InlineKeyboardButton("\u2b50 Open pack", url=f"https://t.me/addemoji/{short}")]]
    return InlineKeyboardMarkup(rows)
