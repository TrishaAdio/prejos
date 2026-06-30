"""/sheet <short_name> — render a whole pack to labeled contact sheet(s)
and send them (plus mapping files) right back to the chat."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time

from pyrogram import filters
from pyrogram.enums import ParseMode

from core.emoji import EmojiInfo, fetch_pack
from core.sheet import render_sheets
from handlers.util import allowed, safe_reply
from ui.text import esc, pack_not_found, progress_text

HTML = ParseMode.HTML
COLS = 10
CELL = 90
CONCURRENCY = 8
TICK = 1.8  # seconds between progress-bar refreshes


async def _edit(message, text: str) -> None:
    try:
        await message.edit_text(text, parse_mode=HTML, disable_web_page_preview=True)
    except Exception:  # noqa: BLE001  (ignore MESSAGE_NOT_MODIFIED / flood)
        pass


async def _download(client, info: EmojiInfo, sem: asyncio.Semaphore) -> bytes | None:
    fid = info.thumb_file_id or info.file_id
    if not fid:
        return None
    async with sem:
        try:
            bio = await client.download_media(fid, in_memory=True)
            bio.seek(0)
            return bio.read()
        except Exception:  # noqa: BLE001
            return None


def register(app) -> None:
    @app.on_message(filters.command("sheet"))
    async def _sheet(client, message):
        if not allowed(message.from_user.id if message.from_user else None):
            return
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

        short = parts[0].strip().rsplit("/", 1)[-1]
        status = await safe_reply(message, f"Reading <code>{esc(short)}</code> \u2026", parse_mode=HTML)

        try:
            infos = await fetch_pack(client, short)
        except Exception:  # noqa: BLE001
            await status.edit_text(pack_not_found(short), parse_mode=HTML)
            return
        if not infos:
            await status.edit_text(pack_not_found(short), parse_mode=HTML)
            return

        # Download every thumbnail concurrently, with a live progress bar + ETA.
        total = len(infos)
        results: list[bytes | None] = [None] * total
        sem = asyncio.Semaphore(CONCURRENCY)
        done = 0
        start_t = time.monotonic()

        async def _worker(idx: int, info: EmojiInfo) -> None:
            nonlocal done
            results[idx] = await _download(client, info, sem)
            done += 1

        tasks = [asyncio.create_task(_worker(i, info)) for i, info in enumerate(infos)]

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
        blobs = results

        await _edit(status, "Building the sheet \u2026")
        items = [(blob, info.id_str[-12:]) for blob, info in zip(blobs, infos)]
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
                        {
                            "index": i,
                            "custom_emoji_id": info.id_str,
                            "emoji": info.emoji,
                            "set_name": info.set_name,
                        }
                        for i, info in enumerate(infos)
                    ],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            map_txt = os.path.join(td, f"{short}_mapping.txt")
            with open(map_txt, "w") as f:
                for info in infos:
                    f.write(f'"{info.slug}": ("{info.id_str}", "{info.emoji}"),\n')

            await _edit(status, f"Uploading {len(sheet_paths)} sheet(s) \u2026")
            for i, p in enumerate(sheet_paths, 1):
                cap = (
                    f"{esc(short)} \u2014 {len(infos)} icons. Labels show the last 12 "
                    f"digits; full ids are in the mapping files."
                    if i == 1
                    else None
                )
                await client.send_document(
                    message.chat.id, p, caption=cap, parse_mode=HTML,
                    reply_to_message_id=message.id,
                )
            await client.send_document(message.chat.id, map_json,
                                       caption="Full custom_emoji_ids in grid order")
            await client.send_document(message.chat.id, map_txt,
                                       caption="Paste-ready name / id / glyph lines")

        try:
            await status.delete()
        except Exception:  # noqa: BLE001
            pass
