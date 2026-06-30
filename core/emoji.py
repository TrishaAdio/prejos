"""Custom-emoji resolution and pack fetching via Pyrogram raw MTProto.

Works for bot sessions (no Premium required). A custom-emoji id is the same as
the underlying document id, so we can resolve ids -> sticker (true base glyph +
pack name) and fetch a whole pack by short name.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from pyrogram import raw, types
from pyrogram.enums import MessageEntityType


@dataclass(slots=True)
class EmojiInfo:
    id: int
    emoji: str          # the associated base glyph (NOT unique across icons)
    set_name: str       # pack short name, if known

    @property
    def id_str(self) -> str:
        return str(self.id)

    @property
    def slug(self) -> str:
        """A default name suggestion derived from the base glyph."""
        if not self.emoji:
            return "icon"
        try:
            return unicodedata.name(self.emoji[0]).lower().split(" ")[0].replace("-", "_")
        except (ValueError, TypeError):
            return "icon"


async def _parse_documents(client, documents) -> list[EmojiInfo]:
    out: list[EmojiInfo] = []
    for item in documents:
        emoji = ""
        set_name = ""
        try:
            attrs = {type(a): a for a in item.attributes}
            sticker = await types.Sticker._parse(client, item, attrs)
            emoji = sticker.emoji or ""
            set_name = sticker.set_name or ""
        except Exception:  # noqa: BLE001
            ce_attr = next(
                (a for a in item.attributes
                 if isinstance(a, raw.types.DocumentAttributeCustomEmoji)),
                None,
            )
            if ce_attr:
                emoji = getattr(ce_attr, "alt", "") or ""
        out.append(EmojiInfo(id=item.id, emoji=emoji, set_name=set_name))
    return out


def extract_ids(message) -> list[int]:
    """Custom-emoji ids found in a message's text/caption entities, in order."""
    ids: list[int] = []
    seen: set[int] = set()
    entities = list(message.entities or []) + list(message.caption_entities or [])
    for ent in entities:
        if ent.type == MessageEntityType.CUSTOM_EMOJI and ent.custom_emoji_id:
            eid = int(ent.custom_emoji_id)
            if eid not in seen:
                seen.add(eid)
                ids.append(eid)
    return ids


async def resolve_ids(client, ids: list[int]) -> dict[int, EmojiInfo]:
    """Resolve custom-emoji ids to EmojiInfo. Missing/invalid ids are omitted."""
    result: dict[int, EmojiInfo] = {}
    ids = [int(i) for i in ids]
    for i in range(0, len(ids), 200):  # Telegram caps at 200 per call
        batch = ids[i : i + 200]
        try:
            docs = await client.invoke(
                raw.functions.messages.GetCustomEmojiDocuments(document_id=batch)
            )
        except Exception:  # noqa: BLE001
            continue
        for info in await _parse_documents(client, docs):
            result[info.id] = info
    return result


async def fetch_pack(client, short_name: str) -> list[EmojiInfo]:
    """Every custom emoji in a pack, by its short name (t.me/addemoji/<name>)."""
    short_name = short_name.strip().rsplit("/", 1)[-1]
    res = await client.invoke(
        raw.functions.messages.GetStickerSet(
            stickerset=raw.types.InputStickerSetShortName(short_name=short_name),
            hash=0,
        )
    )
    infos = await _parse_documents(client, res.documents)
    for info in infos:
        if not info.set_name:
            info.set_name = short_name
    return infos
