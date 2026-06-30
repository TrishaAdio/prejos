"""Presentation layer — polished HTML for a bot that is not 'ordinary'.

House style: bold for emphasis, <code> for tap-to-copy ids/values, <blockquote>
for hints, clean dividers. No italics. No noisy how-to filler.
"""
from __future__ import annotations

import html
import re

from core.emoji import EmojiInfo

BRAND = "prejos"
TAGLINE = "premium custom-emoji inspector"

# Decorative chrome uses plain unicode (always renders, no Premium needed).
DOT = "\u2009\u00b7\u2009"          # thin-spaced middle dot
DIV = "\u2500" * 18                  # ── divider
ARROW = "\u2192"
SPARK = "\u2726"                     # ✦
GEM = "\U0001F48E"
STAR = "\u2b50"                      # generic fallback glyph

_CE_TAG = re.compile(r'<emoji id="\d+">.*?</emoji>', re.DOTALL)


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def ce(eid: int | str, glyph: str) -> str:
    """A custom-emoji tag; Pyrogram renders it as a premium entity."""
    return f'<emoji id="{eid}">{glyph or STAR}</emoji>'


def strip_ce(text: str) -> str:
    """Remove custom-emoji tags for a non-Premium fallback send."""
    return _CE_TAG.sub("", text)


def has_ce(text: str) -> bool:
    return "<emoji id=" in (text or "")


# --------------------------------------------------------------------------- #
# screens
# --------------------------------------------------------------------------- #
def start_text(name: str) -> str:
    return (
        f"{SPARK} <b>{BRAND}</b> {DOT} {TAGLINE}\n"
        f"<code>{DIV}</code>\n"
        f"Hey {esc(name)}. Send me any <b>premium emoji</b> and I hand back its "
        f"exact id with a paste-ready line.\n\n"
        f"<b>What I do</b>\n"
        f"\u2022 Resolve premium emoji {ARROW} id + base glyph + pack\n"
        f"\u2022 Browse a whole pack, icon by icon, with <code>/pack</code>\n"
        f"\u2022 Render a pack to an image sheet with <code>/sheet</code>\n"
        f"\u2022 Inline mode {ARROW} type the bot + a pack name in any chat\n\n"
        f"<blockquote>Reply to a message full of premium emoji, or just drop "
        f"them here. Ids are shown in <code>monospace</code> so a tap copies them.</blockquote>"
    )


def help_text(bot_username: str) -> str:
    at = f"@{bot_username}" if bot_username else "@yourbot"
    return (
        f"{GEM} <b>How to use {BRAND}</b>\n"
        f"<code>{DIV}</code>\n"
        f"<b>Resolve</b>\n"
        f"Send or reply-to a message containing premium emoji. I return each "
        f"id, its base glyph and pack, plus a paste-ready map line.\n\n"
        f"<b>Browse a pack</b>\n"
        f"<code>/pack &lt;short_name&gt;</code>{DOT}the part after "
        f"<code>t.me/addemoji/</code>\n"
        f"Use the {ARROW} buttons to page through every icon.\n\n"
        f"<b>Sheet</b>\n"
        f"<code>/sheet &lt;short_name&gt;</code>{DOT}I render the whole pack to a "
        f"labeled image grid and send it back with a mapping file of full ids.\n\n"
        f"<b>Inline</b>\n"
        f"Type <code>{at} short_name</code> in any chat to pull icons inline.\n\n"
        f"<blockquote>Tip: a custom emoji's base glyph is not unique \u2014 only the "
        f"id identifies it, which is exactly what I give you.</blockquote>"
    )


def _emoji_line(info: EmojiInfo, *, with_paste: bool = True) -> str:
    icon = ce(info.id, info.emoji)
    pack = f"{DOT}<code>{esc(info.set_name)}</code>" if info.set_name else ""
    head = f"{icon} <code>{info.id_str}</code>{DOT}base {esc(info.emoji) or '?'}{pack}"
    if with_paste:
        paste = f'\n<code>"{info.slug}": ("{info.id_str}", "{esc(info.emoji)}"),</code>'
        return head + paste
    return head


def resolved_card(order: list[int], resolved: dict[int, EmojiInfo]) -> str:
    found = [resolved[i] for i in order if i in resolved]
    missing = len(order) - len(found)
    lines = [
        f"{SPARK} <b>Resolved {len(found)} custom emoji</b>",
        f"<code>{DIV}</code>",
    ]
    for info in found:
        lines.append(_emoji_line(info))
        lines.append("")
    if missing:
        lines.append(f"<blockquote>{missing} id(s) could not be resolved.</blockquote>")
    return "\n".join(lines).strip()


def no_emoji_text() -> str:
    return (
        f"{SPARK} <b>Send me premium emoji</b>\n"
        f"<blockquote>Reply to a message that has premium (custom) emoji, or "
        f"drop them right here. Regular emoji have no id to look up.</blockquote>"
    )


def pack_header(short: str, total: int, page: int, pages: int) -> str:
    return (
        f"{GEM} <b>{esc(short)}</b>{DOT}{total} emoji{DOT}page <b>{page}/{pages}</b>\n"
        f"<code>{DIV}</code>"
    )


def pack_page(short: str, window: list[EmojiInfo], page: int, pages: int, total: int) -> str:
    lines = [pack_header(short, total, page, pages)]
    for info in window:
        lines.append(_emoji_line(info, with_paste=True))
        lines.append("")
    return "\n".join(lines).strip()


def pack_not_found(short: str) -> str:
    return (
        f"{SPARK} <b>Pack not found</b>\n"
        f"Could not load <code>{esc(short)}</code>. Check the short name "
        f"(after <code>t.me/addemoji/</code>) and that it is a custom-emoji pack."
    )



def single_emoji(info: EmojiInfo) -> str:
    """A standalone, send-ready block for one emoji (used by inline mode)."""
    return f"{SPARK} {_emoji_line(info)}"



def _bar(frac: float, width: int = 14) -> str:
    frac = max(0.0, min(1.0, frac))
    filled = int(round(frac * width))
    return "\u2588" * filled + "\u2591" * (width - filled)


def humanize_eta(seconds: float) -> str:
    if seconds != seconds or seconds < 0:  # NaN / negative guard
        return "\u2026"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def progress_text(label: str, done: int, total: int, elapsed: float) -> str:
    """A premium progress card: bar + percent + rate + ETA."""
    frac = (done / total) if total else 0.0
    pct = int(frac * 100)
    if done and elapsed > 0:
        rate = done / elapsed
        eta = humanize_eta((total - done) / rate) if rate > 0 else "\u2026"
        rate_s = f"{rate:.0f}/s"
    else:
        eta, rate_s = "\u2026", "\u2026"
    return (
        f"{SPARK} <b>{esc(label)}</b>  {done}/{total}\n"
        f"<code>[{_bar(frac)}] {pct:3d}%</code>\n"
        f"<blockquote>{rate_s}{DOT}ETA {eta}</blockquote>"
    )
