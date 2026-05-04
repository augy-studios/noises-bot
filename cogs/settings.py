import discord
from discord import app_commands
from discord.ext import commands

from database import get_guild_settings, set_noise_channel


class SettingsCog(commands.Cog, name="Settings"):
    """Commands for viewing and managing server settings."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    settings_group = app_commands.Group(name="settings", description="Manage server settings for this bot.")

    @settings_group.command(name="view", description="View all current settings for this server.")
    async def settings_view(self, interaction: discord.Interaction):
        settings = get_guild_settings(interaction.guild_id)

        volume = settings.get("volume", 70)
        pitch = settings.get("pitch", 500)
        channel_id = settings.get("noise_channel")
        random_status = settings.get("random_status", 1)

        channel_mention = (
            f"<#{channel_id}>" if channel_id else "*Not set — will use first VC found*"
        )

        embed = discord.Embed(
            title="⚙️ Server Settings",
            colour=discord.Colour.from_str("#ccffcc"),
        )
        embed.add_field(name="🔊 Volume", value=f"{volume} dB", inline=True)
        embed.add_field(name="🎵 Pitch", value=f"{pitch} Hz", inline=True)
        embed.add_field(name="📺 Noise Channel", value=channel_mention, inline=False)
        embed.add_field(
            name="🎲 Random VC Status",
            value="✅ Enabled" if random_status else "❌ Disabled",
            inline=True,
        )

        guild = interaction.guild
        player = guild.voice_client
        status = "🟢 Active" if (player and player.playing) else "🔴 Inactive"
        embed.add_field(name="📡 Stream Status", value=status, inline=True)

        embed.set_footer(text="Use /volume, /pitch, /randomstatus to change individual settings.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings_group.command(
        name="setchannel",
        description="Set the voice channel for white noise playback.",
    )
    @app_commands.describe(channel="The voice channel to stream white noise into")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def settings_setchannel(
        self, interaction: discord.Interaction, channel: discord.VoiceChannel
    ):
        await interaction.response.defer(ephemeral=True)
        set_noise_channel(interaction.guild_id, channel.id)

        embed = discord.Embed(
            title="📺 Noise Channel Updated",
            description=f"White noise will stream in {channel.mention}.",
            colour=discord.Colour.from_str("#ccffcc"),
        )

        # Trigger reconnect to new channel
        noise_cog = self.bot.get_cog("NoiseCog")
        if noise_cog:
            guild = interaction.guild
            if guild.voice_client:
                await guild.voice_client.disconnect(force=True)
            await noise_cog.start_noise_for_guild(interaction.guild_id)
            embed.set_footer(text="Reconnected to the new channel.")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @settings_group.command(
        name="start",
        description="Manually start the white noise stream for this server.",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def settings_start(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        noise_cog = self.bot.get_cog("NoiseCog")
        if noise_cog:
            success = await noise_cog.start_noise_for_guild(interaction.guild_id)
            if success:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="▶️ Stream Started",
                        description="White noise is now playing.",
                        colour=discord.Colour.from_str("#ccffcc"),
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "❌ Could not start stream. Make sure a voice channel is configured with `/settings setchannel`.",
                    ephemeral=True,
                )
        else:
            await interaction.followup.send("❌ Internal error: NoiseCog not loaded.", ephemeral=True)

    @settings_group.command(
        name="stop",
        description="Manually stop the white noise stream for this server.",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def settings_stop(self, interaction: discord.Interaction):
        noise_cog = self.bot.get_cog("NoiseCog")
        if noise_cog:
            await noise_cog.stop_noise_for_guild(interaction.guild_id)
        embed = discord.Embed(
            title="⏹️ Stream Stopped",
            description="White noise has been stopped.",
            colour=discord.Colour.from_str("#ccffcc"),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings_setchannel.error
    @settings_start.error
    @settings_stop.error
    async def settings_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Manage Channels** permission for this.", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))