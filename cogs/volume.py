import discord
from discord import app_commands
from discord.ext import commands

from database import get_guild_settings, set_volume


class VolumeCog(commands.Cog, name="Volume"):
    """Commands for managing white noise volume."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    volume_group = app_commands.Group(name="volume", description="Manage white noise volume for this server.")

    @volume_group.command(name="view", description="View the current volume setting for this server.")
    async def volume_view(self, interaction: discord.Interaction):
        settings = get_guild_settings(interaction.guild_id)
        vol = settings.get("volume", 70)
        embed = discord.Embed(
            title="🔊 Volume",
            description=f"Current volume: **{vol} dB**\n*(Range: 50–85 dB | Default: 70 dB)*",
            colour=discord.Colour.from_str("#ccffcc"),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @volume_group.command(name="set", description="Set the white noise volume for this server (50–85 dB).")
    @app_commands.describe(level="Volume level in decibels (50–85)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def volume_set(self, interaction: discord.Interaction, level: app_commands.Range[int, 50, 85]):
        set_volume(interaction.guild_id, level)

        # apply to active player
        noise_cog = self.bot.get_cog("NoiseCog")
        if noise_cog:
            guild = interaction.guild
            player = guild.voice_client
            if player:
                from cogs.noise import db_to_lavalink_volume
                await player.set_volume(db_to_lavalink_volume(level))

        embed = discord.Embed(
            title="🔊 Volume Updated",
            description=f"Volume set to **{level} dB**.",
            colour=discord.Colour.from_str("#ccffcc"),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @volume_set.error
    async def volume_set_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Manage Server** permission to change the volume.", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VolumeCog(bot))