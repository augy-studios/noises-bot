import discord
from discord.ext import commands, tasks
import wavelink
import asyncio
import logging
import os
from dotenv import load_dotenv
from database import init_db, get_all_guild_ids

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_HOST = os.getenv("LAVALINK_HOST", "127.0.0.1")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", 2333))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("noises")

COGS = [
    "cogs.volume",
    "cogs.pitch",
    "cogs.settings",
    "cogs.randomstatus",
    "cogs.help",
    "cogs.noise",
]


class NoisesBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        # init db
        init_db()

        # load cogs
        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")

        # connect Lavalink
        nodes = [
            wavelink.Node(
                uri=f"http://{LAVALINK_HOST}:{LAVALINK_PORT}",
                password=LAVALINK_PASSWORD,
            )
        ]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

        # sync slash commands
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} slash command(s).")

        # start status loop
        self.update_status.start()

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_voice_server_update(self, data: dict):
        logger.info(f"Voice server update: endpoint={data.get('endpoint')} guild={data.get('guild_id')}")

    async def on_voice_state_update(self, member, before, after):
        if member == self.user:
            logger.info(f"Bot voice state: before={before.channel} after={after.channel}")

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"Wavelink node '{payload.node.identifier}' is ready.")

    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Restart track on end to keep looping."""
        player: wavelink.Player = payload.player
        if player and player.guild:
            guild_id = player.guild.id
            noise_cog = self.get_cog("NoiseCog")
            if noise_cog:
                await noise_cog.restart_noise(guild_id, player)

    @tasks.loop(minutes=5)
    async def update_status(self):
        """Update playing status with guild count."""
        try:
            guild_count = len(self.guilds)
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{guild_count} guild{'s' if guild_count != 1 else ''}",
            )
            await self.change_presence(activity=activity)
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")

    @update_status.before_loop
    async def before_update_status(self):
        await self.wait_until_ready()


def main():
    bot = NoisesBot()
    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()