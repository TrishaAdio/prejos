"""/sheet <short_name> — render a whole pack to labeled contact sheet(s) and send.

Uses the HTTP Bot API (getStickerSet / getFile / file download / sendDocument).
This deliberately avoids MTProto download_media, which triggers
auth.ExportAuthorization and floods hard when a bot downloads hundreds of files.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import tempfile
import time

from pyrogram import filters
from pyrogram.enums import ParseMode

from core import botapi
from core.emoji import EmojiInfo
from core.sheet import render_sheets
from handlers.util import allowed, safe_reply
from ui.text import esc, pack_not_found, progress_text

HTML = ParseMode.HTML
COLS = 8
CELL = 100
CONCURRENCY = 8          # HTTP downloads — safe, no ExportAuthorization
TICK = 1.8               # progress-bar refresh interval
STALE_AFTER = 90         # ignore commands older than this (drops restart backlog)

_active: set[int] = set()  # chats with an in-flight /sheet


async def _edit(message, text: str) -> None:
    try:
        await message.edit_text(text, parse_mode=HTML, disable_web_page_preview=True)
    except Exception:  # noqa: BLE001
        pass


def register(app) -> None:
    @app.on_message(filters.command("sheet"))
    async def _sheet(client, message):
        if not allowed(message.from_user.id if message.from_user else None):
            return

        # Drop stale commands replayed from the update backlog after a restart.
        try:
            age = (datetime.datetime.now(datetime.timezone.utc)
                   - message.date.replace(tzinfo=datetime.timezone.utc)).total_seconds()
            if age > STALE_AFTER:
                return
        except Exception:  # noqa: BLE001
            pass

        parts = message.command[1:]
        if not parts:
            await safe_reply(
                message,
                "Usage  <code>/sheet &lt;short_name&gt;</code>\n"
                "<blockquote>I render the whole pack to a labeled image grid and "
                "send it here, with a mapping file of the full ids.</blockquote>",
                parse_mode=HTML,
            )
            return

        chat_id = message.chat.id
        if chat_id in _active:
            await safe_reply(message, "Already rendering a sheet here \u2014 hang on.", parse_mode=HTML)
            return
        _active.add(chat_id)
        try:
            await _run(message, parts[0].strip().rsplit("/", 1)[-1])
        finally:
            _active.discard(chat_id)


async def _run(message, short: str) -> None:
    status = await safe_reply(message, f"Reading <code>{esc(short)}</code> \u2026", parse_mode=HTML)

    try:
        data = await botapi.get_sticker_set(short)
    except Exception:  # noqa: BLE001
        await _edit(status, pack_not_found(short))
        return
    stickers = (data or {}).get("stickers") or []
    if not stickers:
        await _edit(status, pack_not_found(short))
        return

    infos = [
        EmojiInfo(
            id=int(s.get("custom_emoji_id") or 0),
            emoji=s.get("emoji") or "",
            set_name=short,
            thumb_file_id=(s.get("thumbnail") or {}).get("file_id") or s.get("file_id") or "",
        )
        for s in stickers
    ]
    total = len(infos)

    # Download thumbnails over HTTP with a live progress bar + ETA.
    results: list[bytes | None] = [None] * total
    sem = asyncio.Semaphore(CONCURRENCY)
    done = 0
    start_t = time.monotonic()

    async def _dl(idx: int, info: EmojiInfo) -> None:
        nonlocal done
        async with sem:
            results[idx] = await botapi.download_file(info.thumb_file_id) if info.thumb_file_id else None
        done += 1

    await _edit(status, progress_text("Downloading", 0, total, 0.0))
    tasks = [asyncio.create_task(_dl(i, info)) for i, info in enumerate(infos)]

    async def _monitor() -> None:
        while done < total:
            await asyncio.sleep(TICK)
            await _edit(status, progress_text("Downloading", done, total, time.monotonic() - start_t))

    mon = asyncio.create_task(_monitor())
    try:
        await asyncio.gather(*tasks)
    finally:
        mon.cancel()
    await _edit(status, progress_text("Downloading", total, total, time.monotonic() - start_t))

    await _edit(status, "Building the sheet \u2026")
    items = [(blob, info.id_str) for blob, info in zip(results, infos)]
    sheets = await asyncio.to_thread(render_sheets, items, cols=COLS, cell=CELL)

    with tempfile.TemporaryDirectory() as td:
        sheet_paths = []
        for n, sheet in enumerate(sheets, 1):
            p = os.path.join(td, f"{short}_sheet_{n}.png")
            sheet.save(p, "PNG")
            sheet_paths.append(p)

        map_json = os.path.join(td, f"{short}_mapping.json")
        with open(map_json, "w") as f:
            json.dump(
                [
                    {"index": i, "custom_emoji_id": info.id_str,
                     "emoji": info.emoji, "set_name": info.set_name}
                    for i, info in enumerate(infos)
                ],
                f, indent=2, ensure_ascii=False,
            )
        map_txt = os.path.join(td, f"{short}_mapping.txt")
        with open(map_txt, "w") as f:
            for info in infos:
                f.write(f'"{info.slug}": ("{info.id_str}", "{info.emoji}"),\n')

        await _edit(status, f"Uploading {len(sheet_paths)} sheet(s) \u2026")
        for i, p in enumerate(sheet_paths, 1):
            cap = (
                f"{esc(short)} \u2014 {total} icons. Full id under each icon "
                f"(two lines); mapping files included."
                if i == 1 else None
            )
            await botapi.send_document(message.chat.id, p, caption=cap, reply_to=message.id)
        await botapi.send_document(message.chat.id, map_json, caption="Full custom_emoji_ids in grid order")
        await botapi.send_document(message.chat.id, map_txt, caption="Paste-ready name / id / glyph lines")

    try:
        await status.delete()
    except Exception:  # noqa: BLE001
        pass
