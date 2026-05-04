import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "noises.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id        INTEGER PRIMARY KEY,
                volume          INTEGER NOT NULL DEFAULT 70,
                pitch           INTEGER NOT NULL DEFAULT 500,
                noise_channel   INTEGER,
                random_status   INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS global_statuses (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                text    TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS guild_statuses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                text        TEXT NOT NULL,
                UNIQUE(guild_id, text)
            );

            CREATE TABLE IF NOT EXISTS disabled_global_statuses (
                guild_id    INTEGER NOT NULL,
                status_id   INTEGER NOT NULL,
                PRIMARY KEY (guild_id, status_id),
                FOREIGN KEY (status_id) REFERENCES global_statuses(id) ON DELETE CASCADE
            );
            """
        )

        # seed default global statuses
        default_statuses = [
            "🌊 Shh... the ocean is thinking",
            "📺 Static. Just vibes.",
            "☁️ Cloud computing (literally)",
            "🧠 Buffering your brain cells",
            "🌫️ Fog machine: engaged",
            "🎲 Rolling for perception... nat 1",
            "🔊 Nothing to see here, keep scrolling",
            "🪴 Growing in silence",
            "🐚 Hear the sea in me",
            "🌌 Waiting for a sign from the void",
            "😴 Lulling you to productivity",
            "📡 Receiving transmissions from nowhere",
            "🔇 Maximum hush achieved",
            "🧊 Chilling (literally)",
            "🕳️ Falling into a noise hole",
            "🎵 White noise? More like RIGHT noise",
            "🛸 Alien frequencies detected",
            "⏳ Time: suspended",
            "💤 zzzz (in audio format)",
            "🌬️ Just wind. Don't worry about it.",
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO global_statuses (text) VALUES (?)",
            [(s,) for s in default_statuses],
        )
        conn.commit()


# ─── Guild Settings ───────────────────────────────────────────────────────────

def ensure_guild(guild_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
        )
        conn.commit()


def get_guild_settings(guild_id: int) -> dict:
    ensure_guild(guild_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        ).fetchone()
        return dict(row) if row else {}


def set_volume(guild_id: int, volume: int):
    ensure_guild(guild_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE guild_settings SET volume = ? WHERE guild_id = ?",
            (volume, guild_id),
        )
        conn.commit()


def set_pitch(guild_id: int, pitch: int):
    ensure_guild(guild_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE guild_settings SET pitch = ? WHERE guild_id = ?",
            (pitch, guild_id),
        )
        conn.commit()


def set_noise_channel(guild_id: int, channel_id: int | None):
    ensure_guild(guild_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE guild_settings SET noise_channel = ? WHERE guild_id = ?",
            (channel_id, guild_id),
        )
        conn.commit()


def set_random_status(guild_id: int, enabled: bool):
    ensure_guild(guild_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE guild_settings SET random_status = ? WHERE guild_id = ?",
            (1 if enabled else 0, guild_id),
        )
        conn.commit()


def get_all_guild_ids() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT guild_id FROM guild_settings").fetchall()
        return [r["guild_id"] for r in rows]


# ─── Random Statuses ──────────────────────────────────────────────────────────

def get_global_statuses() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM global_statuses ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_guild_statuses(guild_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM guild_statuses WHERE guild_id = ? ORDER BY id", (guild_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def add_guild_status(guild_id: int, text: str) -> bool:
    """True if added, False if duplicate."""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO guild_statuses (guild_id, text) VALUES (?, ?)",
                (guild_id, text),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def delete_guild_status(guild_id: int, status_id: int) -> bool:
    """True if deleted."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM guild_statuses WHERE id = ? AND guild_id = ?",
            (status_id, guild_id),
        )
        conn.commit()
        return cur.rowcount > 0


def disable_global_status(guild_id: int, status_id: int) -> bool:
    """True if newly disabled, False if already disabled or not found."""
    # check status exists
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM global_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        if not exists:
            return False
        try:
            conn.execute(
                "INSERT INTO disabled_global_statuses (guild_id, status_id) VALUES (?, ?)",
                (guild_id, status_id),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def enable_global_status(guild_id: int, status_id: int) -> bool:
    """Re-enable a disabled global status."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM disabled_global_statuses WHERE guild_id = ? AND status_id = ?",
            (guild_id, status_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_disabled_global_status_ids(guild_id: int) -> list[int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT status_id FROM disabled_global_statuses WHERE guild_id = ?",
            (guild_id,),
        ).fetchall()
        return [r["status_id"] for r in rows]


def get_active_statuses_for_guild(guild_id: int) -> list[str]:
    """Return active statuses for a guild (global non-disabled + guild-specific)."""
    disabled = set(get_disabled_global_status_ids(guild_id))
    global_statuses = [s for s in get_global_statuses() if s["id"] not in disabled]
    guild_statuses = get_guild_statuses(guild_id)
    return [s["text"] for s in global_statuses] + [s["text"] for s in guild_statuses]