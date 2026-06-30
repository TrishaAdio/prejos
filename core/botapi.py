"""Bot API over HTTP (aiohttp).

Used for the /sheet pipeline (getStickerSet, getFile, file download, sendDocument)
because the HTTP Bot API does NOT use auth.ExportAuthorization — unlike MTProto's
download_media, which floods badly when a bot downloads hundreds of files.
"""
from __future__ import annotations

import json
import os

import aiohttp

from config import config

API = "https://api.telegram.org"
_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
    return _session


async def close() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()


async def _call(method: str, **params) -> dict:
    s = await _get_session()
    url = f"{API}/bot{config.bot_token}/{method}"
    clean = {k: v for k, v in params.items() if v is not None}
    async with s.get(url, params=clean) as r:
        data = await r.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method}: {data.get('description')}")
    return data["result"]


async def get_sticker_set(name: str) -> dict:
    return await _call("getStickerSet", name=name)


async def download_file(file_id: str) -> bytes | None:
    """getFile + HTTP download. No ExportAuthorization involved."""
    try:
        info = await _call("getFile", file_id=file_id)
    except Exception:  # noqa: BLE001
        return None
    path = info.get("file_path")
    if not path:
        return None
    s = await _get_session()
    url = f"{API}/file/bot{config.bot_token}/{path}"
    try:
        async with s.get(url) as r:
            if r.status != 200:
                return None
            return await r.read()
    except Exception:  # noqa: BLE001
        return None


async def send_document(
    chat_id: int | str,
    path: str,
    *,
    caption: str | None = None,
    reply_to: int | None = None,
) -> dict | None:
    s = await _get_session()
    url = f"{API}/bot{config.bot_token}/sendDocument"
    with open(path, "rb") as fh:
        blob = fh.read()
    form = aiohttp.FormData()
    form.add_field("chat_id", str(chat_id))
    if caption:
        form.add_field("caption", caption)
        form.add_field("parse_mode", "HTML")
    if reply_to:
        form.add_field(
            "reply_parameters",
            json.dumps({"message_id": reply_to, "allow_sending_without_reply": True}),
        )
    form.add_field("document", blob, filename=os.path.basename(path),
                   content_type="application/octet-stream")
    try:
        async with s.post(url, data=form) as r:
            return await r.json()
    except Exception:  # noqa: BLE001
        return None
