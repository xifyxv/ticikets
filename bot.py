# Jeff Tweaks Ticket Bot
# Matches the Tickets v2 panel style

import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# ==================== CONFIG ====================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

GUILD_ID = 1464708562046419172  # Your server ID for instant command sync

# Hardcoded IDs from user
TICKET_CATEGORY_ID = 1572673615802011748   # Category where ALL tickets are created
PANEL_CHANNEL_ID = 1565079109225283644     # Channel where the ticket panel is posted
STAFF_ROLE_ID = 1464733541903630437        # Role to ping in every ticket
STAFF_ROLE_NAME = "🛡️・Support"             # Fallback role name
LOG_CHANNEL_NAME = "ticket-logs"           # Optional log channel

# Roles that can see every ticket
TICKET_VIEW_ROLE_IDS = [
    1564028302807670784,
    1464732666359316501,
    1464733541903630437,
]

EMBED_COLOR = 0xFFD700  # Yellow matching the logo

# ==================== BOT SETUP ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

# Simple in-memory ticket tracking (use a database for production)
active_tickets = {}  # channel_id -> user_id

# ==================== HELPERS ====================
def get_staff_role(guild: discord.Guild):
    role = guild.get_role(STAFF_ROLE_ID)
    if role:
        return role
    return discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

def get_ticket_category(guild: discord.Guild):
    category = guild.get_channel(TICKET_CATEGORY_ID)
    if isinstance(category, discord.CategoryChannel):
        return category
    return None

async def log_ticket_action(guild: discord.Guild, message: str):
    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel:
        embed = discord.Embed(description=message, color=EMBED_COLOR, timestamp=datetime.utcnow())
        await log_channel.send(embed=embed)

# ==================== TICKET PANEL VIEW ====================
class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Purchase", style=discord.ButtonStyle.green, emoji="💳", custom_id="ticket_purchase")
    async def purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "purchase")

    @discord.ui.button(label="Support", style=discord.ButtonStyle.blurple, emoji="🛠️", custom_id="ticket_support")
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "support")

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        # Defer immediately so Discord doesn't time out
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild
        user = interaction.user

        # Check if user already has an open ticket
        for channel_id, owner_id in active_tickets.items():
            if owner_id == user.id:
                channel = guild.get_channel(channel_id)
                if channel:
                    await interaction.followup.send(
                        f"You already have an open ticket: {channel.mention}", ephemeral=True
                    )
                    return

        category = get_ticket_category(guild)
        if not category:
            await interaction.followup.send(
                "Ticket category not found. Make sure the category ID is correct and the bot can see it.",
                ephemeral=True
            )
            return

        staff_role = get_staff_role(guild)

        # Overwrites: hide from everyone, show to user + bot + the 3 staff roles
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        # Add the roles that should see tickets
        for role_id in TICKET_VIEW_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        channel_name = f"{ticket_type}-{user.name}".lower().replace(" ", "-")[:90]

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket by {user} | Type: {ticket_type}"
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "**Permission error.** The bot needs **Manage Channels** permission (and permission to manage the ticket category).",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.followup.send(
                f"**Failed to create ticket:**\n```{type(e).__name__}: {e}```",
                ephemeral=True
            )
            return

        active_tickets[ticket_channel.id] = user.id

        # Welcome embed inside the ticket
        embed = discord.Embed(
            title=f"JEFF TWEAKS | {ticket_type.upper()} TICKET",
            description=(
                f"Hello {user.mention},\n\n"
                f"Thank you for opening a **{ticket_type}** ticket.\n"
                "Please describe your issue or request in detail. A staff member will assist you shortly.\n\n"
                "**Response Times:** Our staff will respond as soon as possible."
            ),
            color=EMBED_COLOR
        )
        embed.set_footer(text="24/7 TICKET ACCESS • OFFICIAL ASSISTANCE")

        close_view = TicketControls()
        ping = f"{user.mention} {staff_role.mention}" if staff_role else user.mention
        await ticket_channel.send(content=ping, embed=embed, view=close_view)

        await interaction.followup.send(
            f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True
        )

        await log_ticket_action(guild, f"**Ticket Opened**\nUser: {user.mention}\nType: {ticket_type}\nChannel: {ticket_channel.mention}")

# ==================== TICKET CONTROLS (inside ticket) ====================
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = get_staff_role(interaction.guild)
        if staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only staff can close tickets.", ephemeral=True)
            return

        await interaction.response.send_message("Closing ticket in 5 seconds...", ephemeral=False)
        await log_ticket_action(interaction.guild, f"**Ticket Closed**\nClosed by: {interaction.user.mention}\nChannel: {interaction.channel.mention}")

        active_tickets.pop(interaction.channel.id, None)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except:
            pass

# ==================== SLASH COMMANDS ====================
@tree.command(name="setup-tickets", description="Post the Jeff Tweaks ticket panel")
@app_commands.default_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="JEFF TWEAKS | TICKET CENTRE",
        description=(
            "**24/7 TICKET ACCESS • OFFICIAL ASSISTANCE**\n\n"
            "Welcome to Jeff Tweaks Support!\n\n"
            "Need help with our products, technical issues, purchases or partnerships? "
            "Our team is here to assist you.\n\n"
            "Please select the appropriate ticket category below to ensure your enquiry reaches the right team.\n\n"
            "**Response Times:** Tickets can be submitted 24/7. Our staff will respond as soon as possible, depending on availability."
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="Select your ticket type below")

    view = TicketPanel()

    # Prefer the hardcoded panel channel if it exists
    panel_channel = interaction.guild.get_channel(PANEL_CHANNEL_ID)
    if panel_channel and isinstance(panel_channel, discord.TextChannel):
        await panel_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Ticket panel posted in {panel_channel.mention}", ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, view=view)
        await interaction.followup.send("Ticket panel posted here (panel channel ID not found or invalid).", ephemeral=True)

@tree.command(name="close", description="Close the current ticket")
async def close_command(interaction: discord.Interaction):
    if interaction.channel.id not in active_tickets:
        await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
        return

    staff_role = get_staff_role(interaction.guild)
    if staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only staff can close tickets.", ephemeral=True)
        return

    await interaction.response.send_message("Closing ticket...", ephemeral=False)
    active_tickets.pop(interaction.channel.id, None)
    await interaction.channel.delete(reason=f"Closed by {interaction.user}")

# ==================== EVENTS ====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    # Persistent views
    bot.add_view(TicketPanel())
    bot.add_view(TicketControls())

    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            print(f"Synced commands to guild {GUILD_ID}")
        else:
            await tree.sync()
            print("Synced global commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_guild_channel_delete(channel):
    active_tickets.pop(channel.id, None)

# ==================== RUN ====================
if __name__ == "__main__":
    bot.run(TOKEN)
