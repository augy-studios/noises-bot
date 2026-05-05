import os
import platform
import socket
import sys

import discord
import psutil
from discord import app_commands
from discord.ext import commands


class BotInfoCog(commands.Cog, name="BotInfo"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="botinfo", description="View information about the bot.")
    async def botinfo(self, interaction: discord.Interaction):
        os_info = f"{platform.system()} {platform.release()}"

        start_time = getattr(self.bot, "start_time", None)
        if start_time:
            uptime_secs = int((discord.utils.utcnow() - start_time).total_seconds())
            h, rem = divmod(uptime_secs, 3600)
            m, s = divmod(rem, 60)
            uptime = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            uptime = "N/A"

        hostname = socket.gethostname()
        cpu_arch = platform.machine()
        cpu_cores = os.cpu_count() or 1
        cpu_usage = psutil.cpu_percent(interval=0.1)

        proc = psutil.Process()
        mem_used_mb = proc.memory_info().rss / (1024 ** 2)
        mem_total_gb = psutil.virtual_memory().total / (1024 ** 3)

        python_version = f"v{sys.version.split()[0]}"
        discordpy_version = discord.__version__

        guilds = len(self.bot.guilds)
        channels = sum(len(g.channels) for g in self.bot.guilds)
        users = sum(g.member_count or 0 for g in self.bot.guilds)

        def count_commands(cmds):
            total = 0
            for cmd in cmds:
                if isinstance(cmd, app_commands.Group):
                    total += count_commands(cmd.commands)
                else:
                    total += 1
            return total

        total_commands = count_commands(self.bot.tree.get_commands())

        lines = [
            f"**Operating System**: {os_info}",
            f"**Uptime**: {uptime}",
            f"**Hostname**: {hostname}",
            f"**CPU Architecture**: {cpu_arch} ({cpu_cores} cores)",
            f"**CPU Usage**: {cpu_usage:.0f}%",
            f"**Memory Usage**: {mem_used_mb:.2f}MB / {mem_total_gb:.2f}GB",
            f"**Python Version**: {python_version}",
            f"**discord.py Version**: {discordpy_version}",
            f"**Connected to** {guilds} guild{'s' if guilds != 1 else ''}, {channels} channels, and {users} users",
            f"**Total Commands**: {total_commands}",
        ]

        embed = discord.Embed(
            title="Bot Information",
            description="\n".join(f"• {line}" for line in lines),
            colour=discord.Colour.from_str("#ccffcc"),
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(BotInfoCog(bot))
