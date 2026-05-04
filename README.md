# 🌊 Noises

A Discord bot that delivers **24/7 white noise** to a voice channel of your choosing — even when nobody's in it. Built with `discord.py` and **Lavalink** for robust, persistent voice sessions.

---

## Features

- **24/7 white noise streaming** via Lavalink — stays in VC even with no members
- **Per-guild volume control** (50–85 dB)
- **Per-guild pitch control** (20–4000 Hz) via Lavalink timescale filter
- **Automatic reconnect loop** — bot re-joins and resumes if disconnected
- **Random VC status messages** that rotate every 10 minutes (20 built-in + per-guild custom)
- **Global status management** — admins can disable specific global statuses per server
- **Paginated `/help`** command
- **Playing tag** showing `Listening to X guilds`
- SQLite database for all settings (no external DB required)

---

## Stack

| Component | Technology |
| --- | --- |
| Bot framework | `discord.py` 2.3+ |
| Voice/audio | `wavelink` 3.4+ (Lavalink client) |
| Audio server | Lavalink 4.x (self-hosted) |
| Database | SQLite (via stdlib `sqlite3`) |
| Runtime | Python 3.11+ |
| Process manager | `tmux` |

---

## Prerequisites

- **Python 3.11+**
- **Java 17+** (for Lavalink)
- A Discord bot token with the following intents enabled:
  - `Guilds`
  - `Voice States`

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/augy-studios/noises-bot.git
cd noises-bot
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
nano .env
```

Fill in:

```bash
DISCORD_TOKEN=your_discord_bot_token
LAVALINK_HOST=127.0.0.1
LAVALINK_PORT=2333
LAVALINK_PASSWORD=youshallnotpass
```

### 4. Set up Lavalink

Download the latest Lavalink jar:

```bash
cd lavalink
wget https://github.com/lavalink-devs/Lavalink/releases/latest/download/Lavalink.jar
cd ..
```

The `application.yml` in `lavalink/` is pre-configured. Edit the `password` field if you change it (and update `.env` accordingly).

---

## Running with tmux

### Start Lavalink

```bash
tmux new-session -d -s lavalink \
  'cd lavalink && java -jar Lavalink.jar'
```

Wait ~10 seconds for Lavalink to fully start before launching the bot.

### Start the bot

```bash
tmux new-session -d -s noises \
  'source venv/bin/activate && python bot.py'
```

### Attach to sessions

```bash
tmux attach -t lavalink   # view Lavalink logs
tmux attach -t noises     # view bot logs
```

### Stop

```bash
tmux kill-session -t noises
tmux kill-session -t lavalink
```

---

## Commands

### 🔊 Volume

| Command | Description | Permissions |
| --- | --- | --- |
| `/volume view` | View current volume (dB) | Everyone |
| `/volume set [50–85]` | Set volume in dB | Manage Server |

### 🎵 Pitch

| Command | Description | Permissions |
| --- | --- | --- |
| `/pitch view` | View current pitch (Hz) | Everyone |
| `/pitch set [20–4000]` | Set pitch in Hz | Manage Server |

### ⚙️ Settings

| Command | Description | Permissions |
| --- | --- | --- |
| `/settings view` | View all server settings | Everyone |
| `/settings setchannel [#vc]` | Set the voice channel to stream in | Manage Server |
| `/settings start` | Manually start the noise stream | Manage Server |
| `/settings stop` | Manually stop the noise stream | Manage Server |

### 🎲 Random Status

| Command | Description | Permissions |
| --- | --- | --- |
| `/randomstatus on` | Enable random VC status rotation | Manage Channels |
| `/randomstatus off` | Disable random VC status rotation | Manage Channels |
| `/randomstatus list` | List all statuses (global + server) | Everyone |
| `/randomstatus add [text]` | Add a custom status for this server | Manage Channels |
| `/randomstatus delete [id]` | Delete a server-specific status by ID | Manage Channels |
| `/randomstatus disable [id]` | Hide a global status from this server | Manage Channels |
| `/randomstatus enable [id]` | Re-enable a disabled global status | Manage Channels |

### ❓ Help

| Command | Description |
| --- | --- |
| `/help` | Paginated list of all commands |

---

## How It Works

1. **Lavalink** handles the actual audio streaming. The bot connects to your self-hosted Lavalink node on startup.
2. When a noise channel is set (via `/settings setchannel`), the **reconnect loop** (runs every 2 minutes) ensures the bot is always in that VC and always playing.
3. **Volume** is applied via Lavalink's internal volume multiplier (mapped from dB).
4. **Pitch** is applied via Lavalink's **timescale filter** — frequency is mapped relative to 500 Hz (default = 1.0x pitch multiplier).
5. **Random VC statuses** rotate every 10 minutes using `player.set_channel_status()` from the wavelink API.
6. The **playing tag** (`Listening to X guilds`) updates every 5 minutes.

---

## File Structure

```bash
noises-bot/
├── bot.py                  # Entry point
├── database.py             # SQLite ORM layer
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── cogs/
│   ├── noise.py            # Core voice/Lavalink engine
│   ├── volume.py           # /volume commands
│   ├── pitch.py            # /pitch commands
│   ├── settings.py         # /settings commands
│   ├── randomstatus.py     # /randomstatus commands
│   └── help.py             # /help paginator
└── lavalink/
    └── application.yml     # Lavalink server config
```

---

## Database Schema

```sql
guild_settings          -- per-guild config (volume, pitch, channel, random_status)
global_statuses         -- 20 built-in funny VC status messages
guild_statuses          -- per-guild custom status messages
disabled_global_statuses -- per-guild suppressed global statuses
```

---

## Notes

- The bot uses a **public-domain white noise stream** from the Internet Archive as its audio source. The URL can be changed in `cogs/noise.py` (`WHITE_NOISE_URL`).
- VC status setting requires the bot to have the **Set Voice Channel Status** permission in the target channel.
- Lavalink must be running *before* the bot starts. The bot will log an error and retry if Lavalink is unavailable on startup.
- All slash commands are synced **globally** on startup (may take up to 1 hour to propagate to all guilds on first run).

---

## License

MIT
