import discord
from discord import app_commands
from discord.ext import commands

from database import (
    get_global_statuses,
    get_guild_statuses,
    add_guild_status,
    delete_guild_status,
    disable_global_status,
    enable_global_status,
    get_disabled_global_status_ids,
    set_random_status,
    get_guild_settings,
)

MAX_GUILD_STATUSES = 30
MAX_STATUS_LENGTH = 100


class RandomStatusCog(commands.Cog, name="Random Status"):
    """Commands for managing random voice channel statuses."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    rs_group = app_commands.Group(
        name="randomstatus",
        description="Manage random voice channel status messages.",
    )

    @rs_group.command(name="on", description="Enable random VC status messages for this server.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def rs_on(self, interaction: discord.Interaction):
        set_random_status(interaction.guild_id, True)

        # restart rotation if running
        noise_cog = self.bot.get_cog("NoiseCog")
        if noise_cog:
            noise_cog._start_status_rotation(interaction.guild_id)

        embed = discord.Embed(
            title="🎲 Random VC Status: Enabled",
            description="The bot will now set random funny VC statuses periodically.",
            colour=discord.Colour.from_str("#ccffcc"),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rs_group.command(name="off", description="Disable random VC status messages for this server.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def rs_off(self, interaction: discord.Interaction):
        set_random_status(interaction.guild_id, False)

        noise_cog = self.bot.get_cog("NoiseCog")
        if noise_cog:
            noise_cog._stop_status_rotation(interaction.guild_id)
            # clear VC status
            guild = interaction.guild
            player = guild.voice_client
            if player and player.connected:
                try:
                    await player.channel.edit(status="")
                except Exception:
                    pass

        embed = discord.Embed(
            title="🎲 Random VC Status: Disabled",
            description="The bot will no longer set random VC statuses.",
            colour=discord.Colour.from_str("#ccffcc"),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rs_group.command(name="list", description="List all possible random VC status messages.")
    async def rs_list(self, interaction: discord.Interaction):
        global_statuses = get_global_statuses()
        guild_statuses = get_guild_statuses(interaction.guild_id)
        disabled_ids = set(get_disabled_global_status_ids(interaction.guild_id))

        embeds = []

        # global statuses
        global_lines = []
        for s in global_statuses:
            disabled_tag = " ~~[disabled]~~" if s["id"] in disabled_ids else ""
            global_lines.append(f"`{s['id']:>3}` {s['text']}{disabled_tag}")

        global_text = "\n".join(global_lines) if global_lines else "*None*"

        embed1 = discord.Embed(
            title="🌐 Global VC Statuses",
            description=global_text[:4000],
            colour=discord.Colour.from_str("#ccffcc"),
        )
        embed1.set_footer(text="Use /randomstatus disable [id] to hide a global status for this server.")
        embeds.append(embed1)

        # guild statuses
        if guild_statuses:
            guild_lines = [f"`{s['id']:>5}` {s['text']}" for s in guild_statuses]
            guild_text = "\n".join(guild_lines)
            embed2 = discord.Embed(
                title=f"🏠 {interaction.guild.name}'s Custom Statuses",
                description=guild_text[:4000],
                colour=discord.Colour.from_str("#aaffaa"),
            )
            embed2.set_footer(text="Use /randomstatus delete [id] to remove a server status.")
            embeds.append(embed2)
        else:
            embed1.add_field(
                name=f"🏠 {interaction.guild.name}'s Custom Statuses",
                value="*None yet - use /randomstatus add to add some!*",
                inline=False,
            )

        await interaction.response.send_message(embeds=embeds[:2], ephemeral=True)

    @rs_group.command(name="add", description="Add a custom VC status message for this server.")
    @app_commands.describe(text="The status message to add (max 100 characters)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def rs_add(self, interaction: discord.Interaction, text: str):
        if len(text) > MAX_STATUS_LENGTH:
            await interaction.response.send_message(
                f"❌ Status message must be {MAX_STATUS_LENGTH} characters or fewer.", ephemeral=True
            )
            return

        existing = get_guild_statuses(interaction.guild_id)
        if len(existing) >= MAX_GUILD_STATUSES:
            await interaction.response.send_message(
                f"❌ This server has reached the maximum of {MAX_GUILD_STATUSES} custom statuses.",
                ephemeral=True,
            )
            return

        added = add_guild_status(interaction.guild_id, text)
        if added:
            embed = discord.Embed(
                title="✅ Status Added",
                description=f"Added: **{text}**",
                colour=discord.Colour.from_str("#ccffcc"),
            )
        else:
            embed = discord.Embed(
                title="⚠️ Duplicate",
                description="That status already exists for this server.",
                colour=discord.Colour.yellow(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rs_group.command(name="delete", description="Delete a custom VC status added by this server.")
    @app_commands.describe(id="The ID of the guild status to delete (from /randomstatus list)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def rs_delete(self, interaction: discord.Interaction, id: int):
        deleted = delete_guild_status(interaction.guild_id, id)
        if deleted:
            embed = discord.Embed(
                title="🗑️ Status Deleted",
                description=f"Guild status ID `{id}` has been removed.",
                colour=discord.Colour.from_str("#ccffcc"),
            )
        else:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"No guild status with ID `{id}` found for this server.",
                colour=discord.Colour.red(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rs_group.command(name="disable", description="Disable a global VC status for this server only.")
    @app_commands.describe(id="The ID of the global status to disable (from /randomstatus list)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def rs_disable(self, interaction: discord.Interaction, id: int):
        result = disable_global_status(interaction.guild_id, id)
        if result:
            embed = discord.Embed(
                title="🚫 Global Status Disabled",
                description=f"Global status ID `{id}` is now hidden for this server.\nUse `/randomstatus enable {id}` to re-enable it.",
                colour=discord.Colour.from_str("#ccffcc"),
            )
        else:
            disabled_ids = set(get_disabled_global_status_ids(interaction.guild_id))
            if id in disabled_ids:
                embed = discord.Embed(
                    title="⚠️ Already Disabled",
                    description=f"Global status ID `{id}` is already disabled for this server.",
                    colour=discord.Colour.yellow(),
                )
            else:
                embed = discord.Embed(
                    title="❌ Not Found",
                    description=f"No global status with ID `{id}` exists.",
                    colour=discord.Colour.red(),
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rs_group.command(name="enable", description="Re-enable a previously disabled global VC status.")
    @app_commands.describe(id="The ID of the global status to re-enable")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def rs_enable(self, interaction: discord.Interaction, id: int):
        result = enable_global_status(interaction.guild_id, id)
        if result:
            embed = discord.Embed(
                title="✅ Global Status Re-enabled",
                description=f"Global status ID `{id}` is now active for this server again.",
                colour=discord.Colour.from_str("#ccffcc"),
            )
        else:
            embed = discord.Embed(
                title="⚠️ Not Disabled",
                description=f"Global status ID `{id}` was not disabled for this server.",
                colour=discord.Colour.yellow(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rs_on.error
    @rs_off.error
    @rs_add.error
    @rs_delete.error
    @rs_disable.error
    @rs_enable.error
    async def rs_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Manage Channels** permission for this.", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RandomStatusCog(bot))