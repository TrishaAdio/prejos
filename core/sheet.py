"""Contact-sheet rendering (pure Pillow, no network).

Takes pre-downloaded icon bytes + labels and lays them out in a labeled grid.
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

_FONT_PATHS = (
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "DejaVuSans.ttf",
)


def _load_font(size: int):
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _decode(blob: bytes, cell: int) -> Image.Image:
    img = Image.open(BytesIO(blob)).convert("RGBA")
    img.thumbnail((cell, cell), Image.LANCZOS)
    canvas = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
    canvas.paste(img, ((cell - img.width) // 2, (cell - img.height) // 2), img)
    return canvas


def _placeholder(cell: int, label: str, font) -> Image.Image:
    canvas = Image.new("RGBA", (cell, cell), (44, 44, 44, 255))
    d = ImageDraw.Draw(canvas)
    d.rectangle([1, 1, cell - 2, cell - 2], outline=(110, 110, 110, 255))
    d.text((cell / 2, cell / 2), label, fill=(200, 200, 200, 255), font=font, anchor="mm")
    return canvas


def _wrap_id(label: str, font, max_w: int) -> list[str]:
    """Split a long numeric id into lines that each fit within max_w pixels."""
    if not label:
        return [""]
    # find how many chars fit per line at this font
    per = len(label)
    while per > 1 and font.getlength("0" * per) > max_w:
        per -= 1
    if per >= len(label):
        return [label]
    return [label[i : i + per] for i in range(0, len(label), per)]


def render_sheets(
    items: list[tuple[bytes | None, str]],
    *,
    cols: int = 8,
    cell: int = 100,
    max_rows: int = 24,
    bg=(24, 24, 24, 255),
) -> list[Image.Image]:
    """items: list of (icon_bytes_or_None, full_id_label). Returns RGB sheet images.

    The full id is printed under each icon, wrapped across as many lines as needed.
    """
    font = _load_font(max(11, cell // 9))
    pad = 8
    try:
        line_h = font.getbbox("0")[3] + 2
    except Exception:  # noqa: BLE001
        line_h = max(12, cell // 8)
    max_label_w = cell + pad - 2

    # Decode icons + pre-wrap every label so we know the tallest label block.
    decoded: list[tuple[Image.Image, list[str]]] = []
    max_lines = 1
    for blob, label in items:
        try:
            img = _decode(blob, cell) if blob else _placeholder(cell, "?", font)
        except Exception:  # noqa: BLE001
            img = _placeholder(cell, "?", font)
        lines = _wrap_id(label, font, max_label_w)
        max_lines = max(max_lines, len(lines))
        decoded.append((img, lines))

    label_h = max_lines * line_h + 4
    cw = cell + pad
    ch = cell + label_h + pad

    sheets: list[Image.Image] = []
    per_sheet = cols * max_rows
    for start in range(0, len(decoded), per_sheet):
        chunk = decoded[start : start + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * cw + pad, rows * ch + pad), bg)
        draw = ImageDraw.Draw(sheet)
        for i, (img, lines) in enumerate(chunk):
            r, c = divmod(i, cols)
            x = pad + c * cw
            y = pad + r * ch
            sheet.alpha_composite(img, (x, y))
            ty = y + cell + 2
            for ln in lines:
                draw.text((x + cell / 2, ty), ln, fill=(235, 235, 235, 255),
                          font=font, anchor="ma")
                ty += line_h
        sheets.append(sheet.convert("RGB"))
    return sheets
