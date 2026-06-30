# prejos

A polished Telegram **custom-emoji inspector** bot. Send it premium emoji and it
hands back the exact `custom_emoji_id` with a paste-ready map line — because the
id is the only thing that truly identifies a premium icon (the base glyph is not
unique). Browse whole packs, page through them with buttons, or pull icons inline
into any chat.

Built with Pyrogram. Not an "ordinary" bot: clean HTML formatting, inline
keyboards, inline mode, and a colored terminal setup wizard.

## Features

- **Resolve** — send (or reply to) any message with premium emoji → each id, its
  base glyph, pack, and a `"name": ("id", "glyph"),` line ready to paste.
- **`/pack <short_name>`** — browse an entire emoji pack with `← / →` pagination.
- **Inline mode** — type the bot + a pack name in any chat to send icons inline.
- Graceful fallback: if a premium-gated send is rejected, it retries without the
  custom-emoji entity instead of failing.

## Setup

```bash
pip install -r requirements.txt
python setup.py          # colored wizard → writes .env  (API_ID, API_HASH, BOT_TOKEN)
python bot.py            # run
```

Get `API_ID` / `API_HASH` from https://my.telegram.org and `BOT_TOKEN` from
[@BotFather](https://t.me/BotFather). You can also copy `.env.example` to `.env`
and fill it by hand.

## Commands

| Command | What |
|---|---|
| `/start` | Welcome + inline buttons |
| `/help` | Usage |
| `/pack <short> [page]` | Browse a pack (short name = the part after `t.me/addemoji/`) |
| (send emoji) | Resolve premium emoji to ids |
| `@bot <pack>` | Inline mode |

## Layout

```
prejos/
├── bot.py            # entrypoint
├── setup.py          # colorama setup wizard
├── config.py         # .env loader
├── core/emoji.py     # resolve ids + fetch packs (raw MTProto)
├── ui/text.py        # HTML formatting
├── ui/keyboards.py   # inline keyboards
└── handlers/         # start, resolve, pack, inline
```

## Note on Premium

Rendering custom-emoji icons in a sent message depends on the bot's setup; where
it isn't permitted, the bot still returns the full id and the real base glyph
(from Telegram), so you can always tell which icon an id is.
