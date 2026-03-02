import discord
from discord.ext import tasks
import random
import os
import json
from dotenv import load_dotenv
import asyncio

# -----------------------------
# Load Token
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# -----------------------------
# Intents
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True

CONFIG_FILE = "config.json"
VERSE_FILE = "nkjv_verses.json"


# -----------------------------
# Config Handling
# -----------------------------
def load_config():

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f)

    with open(CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# -----------------------------
# Verse Database
# -----------------------------
def load_verses():
    try:
        with open(VERSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def get_random_verse():
    verses = load_verses()

    if not verses:
        return "John 3:16", "For God so loved the world..."

    verse = random.choice(verses)

    reference = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
    text = verse["text"]

    return reference, text


# -----------------------------
# Bot Setup
# -----------------------------
class MyBot(discord.Client):

    def __init__(self):
        super().__init__(intents=intents)

        from discord import app_commands
        self.tree = app_commands.CommandTree(self)

        # Store running tasks per guild
        self.guild_tasks = {}

    async def setup_hook(self):
        await self.tree.sync()


bot = MyBot()


# -----------------------------
# Verse Sending Function
# -----------------------------
async def send_verse(channel):

    reference, text = get_random_verse()

    embed = discord.Embed(
        title="📖 Daily Bible Verse",
        description=text,
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Reference",
        value=reference,
        inline=False
    )

    await channel.send(embed=embed)


# -----------------------------
# Start Recovery Loop For Guild
# -----------------------------
async def start_guild_loop(guild_id, channel):

    # Stop old loop if exists
    if guild_id in bot.guild_tasks:
        bot.guild_tasks[guild_id].cancel()

    async def loop_task():

        await bot.wait_until_ready()

        while True:
            await send_verse(channel)

            # 24 hour delay
            await asyncio.sleep(86400)

    bot.guild_tasks[guild_id] = bot.loop.create_task(loop_task())


# -----------------------------
# Slash Command
# -----------------------------
@bot.tree.command(name="bible_channel")
async def bible_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    config = load_config()

    gid = str(interaction.guild.id)

    if gid not in config:
        config[gid] = {}

    config[gid]["channel"] = channel.id
    save_config(config)

    # Send first verse immediately
    await send_verse(channel)

    # Start 24 hour recovery loop
    await start_guild_loop(gid, channel)

    await interaction.response.send_message(
        f"✅ Daily verses will continue in {channel.mention}",
        ephemeral=True
    )


# -----------------------------
# Auto Recovery On Startup ⭐
# -----------------------------
@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    config = load_config()

    # Restart loops for all saved servers
    for guild_id, settings in config.items():

        if not isinstance(settings, dict):
            continue

        if "channel" not in settings:
            continue

        channel = bot.get_channel(settings["channel"])

        if channel:
            print(f"Recovering verse schedule for guild {guild_id}")
            bot.loop.create_task(start_guild_loop(guild_id, channel))


# -----------------------------
# Run Bot
# -----------------------------
bot.run(TOKEN)
