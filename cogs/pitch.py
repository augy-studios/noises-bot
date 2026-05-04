import discord
from discord import app_commands
from discord.ext import commands

from database import get_guild_settings, set_pitch


class PitchCog(commands.Cog, name="Pitch"):
    """Commands for managing white noise pitch."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    pitch_group = app_commands.Group(name="pitch", description="Manage white noise pitch for this server.")

    @pitch_group.command(name="view", description="View the current pitch setting for this server.")
    async def pitch_view(self, interaction: discord.Interaction):
        settings = get_guild_settings(interaction.guild_id)
        pitch = settings.get("pitch", 500)
        embed = discord.Embed(
            title="🎵 Pitch",
            description=f"Current pitch: **{pitch} Hz**\n*(Range: 20–4000 Hz | Default: 500 Hz)*",
            colour=discord.Colour.from_str("#ccffcc"),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @pitch_group.command(name="set", description="Set the white noise pitch for this server (20–4000 Hz).")
    @app_commands.describe(frequency="Pitch frequency in hertz (20–4000)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def pitch_set(self, interaction: discord.Interaction, frequency: app_commands.Range[int, 20, 4000]):
        set_pitch(interaction.guild_id, frequency)

        # apply to active player
        guild = interaction.guild
        player = guild.voice_client
        if player:
            import wavelink
            from cogs.noise import hz_to_timescale_pitch
            filters = wavelink.Filters()
            filters.timescale.set(pitch=hz_to_timescale_pitch(frequency), speed=1.0, rate=1.0)
            await player.set_filters(filters, seek=False)

        embed = discord.Embed(
            title="🎵 Pitch Updated",
            description=f"Pitch set to **{frequency} Hz**.",
            colour=discord.Colour.from_str("#ccffcc"),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @pitch_set.error
    async def pitch_set_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Manage Server** permission to change the pitch.", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PitchCog(bot))