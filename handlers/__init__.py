"""Handler registration."""
from __future__ import annotations

from handlers import inline, pack, resolve, sheet, start


def register_all(app) -> None:
    start.register(app)
    pack.register(app)
    sheet.register(app)
    inline.register(app)
    resolve.register(app)  # broad private catch-all goes last
