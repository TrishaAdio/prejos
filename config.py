"""Configuration loader for prejos.

Reads credentials from the environment / a .env file. Run setup.py for a
colored interactive wizard that writes the .env for you.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str) -> set[int]:
    out: set[int] = set()
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.add(int(part))
    return out


@dataclass(slots=True)
class Config:
    api_id: int = 0
    api_hash: str = ""
    bot_token: str = ""
    allowed_users: set[int] = field(default_factory=set)

    @classmethod
    def load(cls) -> "Config":
        api_id_raw = os.environ.get("API_ID", "").strip()
        return cls(
            api_id=int(api_id_raw) if api_id_raw.isdigit() else 0,
            api_hash=os.environ.get("API_HASH", "").strip(),
            bot_token=os.environ.get("BOT_TOKEN", "").strip(),
            allowed_users=_parse_ids(os.environ.get("ALLOWED_USERS", "")),
        )

    @property
    def is_complete(self) -> bool:
        return bool(self.api_id and self.api_hash and self.bot_token)

    def missing(self) -> list[str]:
        miss = []
        if not self.api_id:
            miss.append("API_ID")
        if not self.api_hash:
            miss.append("API_HASH")
        if not self.bot_token:
            miss.append("BOT_TOKEN")
        return miss


config = Config.load()
