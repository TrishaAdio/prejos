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


def render_sheets(
    items: list[tuple[bytes | None, str]],
    *,
    cols: int = 10,
    cell: int = 90,
    max_rows: int = 24,
    bg=(24, 24, 24, 255),
) -> list[Image.Image]:
    """items: list of (icon_bytes_or_None, label). Returns RGB sheet images."""
    font = _load_font(max(11, cell // 8))
    pad = 8
    label_h = max(14, cell // 6)
    cw = cell + pad
    ch = cell + label_h + pad

    cells: list[tuple[Image.Image, str]] = []
    for blob, label in items:
        try:
            img = _decode(blob, cell) if blob else _placeholder(cell, "?", font)
        except Exception:  # noqa: BLE001
            img = _placeholder(cell, "?", font)
        cells.append((img, label))

    sheets: list[Image.Image] = []
    per_sheet = cols * max_rows
    for start in range(0, len(cells), per_sheet):
        chunk = cells[start : start + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * cw + pad, rows * ch + pad), bg)
        draw = ImageDraw.Draw(sheet)
        for i, (img, label) in enumerate(chunk):
            r, c = divmod(i, cols)
            x = pad + c * cw
            y = pad + r * ch
            sheet.alpha_composite(img, (x, y))
            draw.text((x + cell / 2, y + cell + 2), label, fill=(235, 235, 235, 255),
                      font=font, anchor="ma")
        sheets.append(sheet.convert("RGB"))
    return sheets
