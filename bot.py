#!/usr/bin/env python3
"""prejos — entrypoint.

Builds the Pyrogram bot client, registers handlers and runs. If credentials are
missing it points you at the colored setup wizard instead of crashing.
"""
from __future__ import annotations

import sys

from config import config


def _require_config() -> None:
    if config.is_complete:
        return
    miss = ", ".join(config.missing())
    print("prejos is not configured yet.")
    print(f"  missing: {miss}")
    print("  run the wizard:  python setup.py")
    sys.exit(1)


def build_app():
    from pyrogram import Client

    return Client(
        "prejos",
        api_id=config.api_id,
        api_hash=config.api_hash,
        bot_token=config.bot_token,
        sleep_threshold=60,  # auto-wait through short floods instead of raising
    )


def main() -> None:
    _require_config()
    from handlers import register_all

    app = build_app()
    register_all(app)
    print("prejos is running.  Press Ctrl+C to stop.")
    app.run()


if __name__ == "__main__":
    main()
