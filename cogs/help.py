import discord
from discord import app_commands
from discord.ext import commands

COMMANDS_DATA = [
    {
        "category": "🔊 Volume",
        "commands": [
            {
                "name": "/volume view",
                "description": "View the current volume for this server.",
                "usage": "/volume view",
                "permissions": "Everyone",
            },
            {
                "name": "/volume set [level]",
                "description": "Set the volume (50–85 dB). Default: 70 dB.",
                "usage": "/volume set level:75",
                "permissions": "Manage Server",
            },
        ],
    },
    {
        "category": "🎵 Pitch",
        "commands": [
            {
                "name": "/pitch view",
                "description": "View the current pitch for this server.",
                "usage": "/pitch view",
                "permissions": "Everyone",
            },
            {
                "name": "/pitch set [frequency]",
                "description": "Set the pitch (20–4000 Hz). Default: 500 Hz.",
                "usage": "/pitch set frequency:800",
                "permissions": "Manage Server",
            },
        ],
    },
    {
        "category": "⚙️ Settings",
        "commands": [
            {
                "name": "/settings view",
                "description": "View all current settings for this server.",
                "usage": "/settings view",
                "permissions": "Everyone",
            },
            {
                "name": "/settings setchannel [channel]",
                "description": "Set the voice channel for white noise playback.",
                "usage": "/settings setchannel channel:#chill-vc",
                "permissions": "Manage Server",
            },
            {
                "name": "/settings start",
                "description": "Manually start the white noise stream.",
                "usage": "/settings start",
                "permissions": "Manage Server",
            },
            {
                "name": "/settings stop",
                "description": "Manually stop the white noise stream.",
                "usage": "/settings stop",
                "permissions": "Manage Server",
            },
        ],
    },
    {
        "category": "🎲 Random Status",
        "commands": [
            {
                "name": "/randomstatus on",
                "description": "Enable random funny VC status messages.",
                "usage": "/randomstatus on",
                "permissions": "Manage Channels",
            },
            {
                "name": "/randomstatus off",
                "description": "Disable random VC status messages.",
                "usage": "/randomstatus off",
                "permissions": "Manage Channels",
            },
            {
                "name": "/randomstatus list",
                "description": "List all possible VC status messages (global + server).",
                "usage": "/randomstatus list",
                "permissions": "Everyone",
            },
            {
                "name": "/randomstatus add [text]",
                "description": "Add a custom VC status message for this server.",
                "usage": "/randomstatus add text:✨ vibing in the static",
                "permissions": "Manage Channels",
            },
            {
                "name": "/randomstatus delete [id]",
                "description": "Delete a custom status added by this server by ID.",
                "usage": "/randomstatus delete id:42",
                "permissions": "Manage Channels",
            },
            {
                "name": "/randomstatus disable [id]",
                "description": "Hide a global status from this server by ID.",
                "usage": "/randomstatus disable id:5",
                "permissions": "Manage Channels",
            },
            {
                "name": "/randomstatus enable [id]",
                "description": "Re-enable a previously disabled global status by ID.",
                "usage": "/randomstatus enable id:5",
                "permissions": "Manage Channels",
            },
        ],
    },
    {
        "category": "❓ Help",
        "commands": [
            {
                "name": "/help",
                "description": "Show this help menu.",
                "usage": "/help",
                "permissions": "Everyone",
            },
        ],
    },
]


def build_page_embed(page_index: int, total_pages: int) -> discord.Embed:
    cat = COMMANDS_DATA[page_index]
    embed = discord.Embed(
        title=f"{cat['category']}",
        colour=discord.Colour.from_str("#ccffcc"),
    )
    for cmd in cat["commands"]:
        value = (
            f"{cmd['description']}\n"
            f"**Usage:** `{cmd['usage']}`\n"
            f"**Permissions:** {cmd['permissions']}"
        )
        embed.add_field(name=cmd["name"], value=value, inline=False)
    embed.set_footer(text=f"Page {page_index + 1}/{total_pages} — White noise, 24/7.")
    return embed


class HelpPaginatorView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=120)
        self.page = 0
        self.total = len(COMMANDS_DATA)
        self.original_interaction = interaction

    async def update(self, interaction: discord.Interaction):
        embed = build_page_embed(self.page, self.total)
        self._update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    def _update_buttons(self):
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page == self.total - 1

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        await self.update(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await self.update(interaction)

    async def on_timeout(self):
        # disable buttons
        for item in self.children:
            item.disabled = True
        try:
            await self.original_interaction.edit_original_response(view=self)
        except Exception:
            pass


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all available commands.")
    async def help_cmd(self, interaction: discord.Interaction):
        view = HelpPaginatorView(interaction)
        view.next_btn.disabled = len(COMMANDS_DATA) <= 1
        embed = build_page_embed(0, len(COMMANDS_DATA))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))