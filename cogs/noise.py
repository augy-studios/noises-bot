"""NoiseCog — Lavalink voice connections and white noise playback per guild."""

import asyncio
import logging
import os
import random
from typing import Optional

import discord
import wavelink
from discord.ext import commands, tasks

from database import (
    get_guild_settings,
    get_active_statuses_for_guild,
)

logger = logging.getLogger("noises.noise")

WHITE_NOISE_URL = "file://" + os.path.abspath("white-noise-1h.mp3")


def db_to_lavalink_volume(db: int) -> int:
    """Convert dB (50–85) to Lavalink volume (0–1000). 70dB → 100."""
    import math
    return max(1, min(1000, round(100 * (10 ** ((db - 70) / 20)))))


def hz_to_timescale_pitch(hz: int) -> float:
    """Map Hz (20–4000) to Lavalink timescale pitch multiplier. 500Hz → 1.0."""
    return max(0.1, min(5.0, hz / 500.0))


class NoiseCog(commands.Cog, name="NoiseCog"):
    """Manages voice connections and white noise streams."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> status rotation Task
        self._status_tasks: dict[int, asyncio.Task] = {}
        self.reconnect_loop.start()

    def cog_unload(self):
        self.reconnect_loop.cancel()
        for task in self._status_tasks.values():
            task.cancel()

    # ─── Internal helpers ──────────────────────────────────────────────────────

    async def _get_or_create_player(
        self, guild: discord.Guild, channel: discord.VoiceChannel
    ) -> Optional[wavelink.Player]:
        """Get or connect a player for the channel."""
        player: wavelink.Player = guild.voice_client  # type: ignore
        if player is None:
            try:
                player = await channel.connect(cls=wavelink.Player, self_deaf=True)
                logger.info(f"[{guild.name}] Connected to VC '{channel.name}'")
            except Exception as e:
                logger.error(f"[{guild.name}] Failed to connect to VC: {e}")
                return None
        return player

    async def _apply_filters(self, player: wavelink.Player, volume_db: int, pitch_hz: int):
        """Apply volume and pitch filters."""
        lava_vol = db_to_lavalink_volume(volume_db)
        pitch_mul = hz_to_timescale_pitch(pitch_hz)

        filters = wavelink.Filters()
        filters.timescale.set(pitch=pitch_mul, speed=1.0, rate=1.0)
        await player.set_filters(filters, seek=False)
        await player.set_volume(lava_vol)

    async def _play_noise(self, player: wavelink.Player, guild_id: int):
        """Fetch and play white noise."""
        settings = get_guild_settings(guild_id)
        volume_db = settings.get("volume", 70)
        pitch_hz = settings.get("pitch", 500)

        await self._apply_filters(player, volume_db, pitch_hz)

        try:
            tracks = await wavelink.Playable.search(WHITE_NOISE_URL)
            track = tracks[0] if isinstance(tracks, list) else tracks.tracks[0] if tracks else None
        except Exception as e:
            logger.error(f"[Guild {guild_id}] Failed to load white noise: {e}")
            return

        if track is None:
            logger.error(f"[Guild {guild_id}] Could not load white noise source.")
            return

        await player.play(track, volume=db_to_lavalink_volume(volume_db))
        logger.info(f"[Guild {guild_id}] Now playing white noise: {track.title}")

    async def restart_noise(self, guild_id: int, player: wavelink.Player):
        """Restart noise when a track ends."""
        if player and player.connected:
            await self._play_noise(player, guild_id)

    async def start_noise_for_guild(self, guild_id: int) -> bool:
        """Start noise for a guild; returns True on success."""
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return False

        settings = get_guild_settings(guild_id)
        channel_id = settings.get("noise_channel")

        if channel_id:
            channel = guild.get_channel(channel_id)
        else:
            # use first VC found
            channel = next(
                (c for c in guild.channels if isinstance(c, discord.VoiceChannel)), None
            )

        if channel is None:
            logger.warning(f"[{guild.name}] No voice channel found to join.")
            return False

        player = await self._get_or_create_player(guild, channel)
        if player is None:
            return False

        if not player.playing:
            await self._play_noise(player, guild_id)

        # start status rotation
        if settings.get("random_status", 1):
            self._start_status_rotation(guild_id)

        return True

    async def stop_noise_for_guild(self, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild and guild.voice_client:
            await guild.voice_client.disconnect(force=True)
        self._stop_status_rotation(guild_id)

    # ─── VC Status Rotation ────────────────────────────────────────────────────

    def _start_status_rotation(self, guild_id: int):
        if guild_id in self._status_tasks and not self._status_tasks[guild_id].done():
            return
        task = asyncio.create_task(self._rotate_status(guild_id))
        self._status_tasks[guild_id] = task

    def _stop_status_rotation(self, guild_id: int):
        task = self._status_tasks.pop(guild_id, None)
        if task:
            task.cancel()

    async def _rotate_status(self, guild_id: int):
        """Rotate VC status every 10 min."""
        await self.bot.wait_until_ready()
        while True:
            try:
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    break
                player: wavelink.Player = guild.voice_client  # type: ignore
                if player is None or not player.connected:
                    break

                statuses = get_active_statuses_for_guild(guild_id)
                if statuses:
                    chosen = random.choice(statuses)
                    try:
                        await player.channel.edit(status=chosen)
                        logger.debug(f"[{guild.name}] VC status set: {chosen}")
                    except Exception as e:
                        logger.warning(f"[{guild.name}] Could not set VC status: {e}")

                await asyncio.sleep(600)  # 10 min
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Guild {guild_id}] Status rotation error: {e}")
                await asyncio.sleep(60)

    # ─── Reconnect loop ────────────────────────────────────────────────────────

    @tasks.loop(minutes=2)
    async def reconnect_loop(self):
        """Check all guilds and reconnect if disconnected or not playing."""
        from database import get_all_guild_ids, get_guild_settings

        for guild_id in get_all_guild_ids():
            try:
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    continue
                settings = get_guild_settings(guild_id)
                channel_id = settings.get("noise_channel")
                # skip guilds without explicit channel
                if not channel_id:
                    continue
                player: wavelink.Player = guild.voice_client  # type: ignore
                if player is None or not player.connected or not player.playing:
                    logger.info(
                        f"[{guild.name}] Reconnect loop: restarting noise stream."
                    )
                    await self.start_noise_for_guild(guild_id)
            except Exception as e:
                logger.error(f"[Guild {guild_id}] Reconnect loop error: {e}")

    @reconnect_loop.before_loop
    async def before_reconnect_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)  # wait for Lavalink


async def setup(bot: commands.Bot):
    await bot.add_cog(NoiseCog(bot))