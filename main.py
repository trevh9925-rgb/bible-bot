import discord
from discord.ext import tasks
import random
import os
import json
from dotenv import load_dotenv
from flask import Flask
import threading

# -----------------------------
# Load Token
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# -----------------------------
# Flask Keep Alive Server ⭐
# -----------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# -----------------------------
# Intents
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True

CONFIG_FILE = "config.json"
VERSE_FILE = "nkjv_verses.json"


# -----------------------------
# Config Handling (Safe)
# -----------------------------
def load_config():

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f)

    with open(CONFIG_FILE, "r") as f:
        try:
            data = json.load(f)

            # Fix old format if needed
            fixed = {}

            for guild_id, settings in data.items():
                if isinstance(settings, int):
                    fixed[guild_id] = {"channel": settings}
                else:
                    fixed[guild_id] = settings

            return fixed

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

        self.guild_tasks = {}

    async def setup_hook(self):
        await self.tree.sync()


bot = MyBot()


# -----------------------------
# Send Verse Function
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
# Start Daily Loop Per Guild
# -----------------------------
async def start_guild_loop(guild_id, channel):

    if guild_id in bot.guild_tasks:
        bot.guild_tasks[guild_id].cancel()

    async def loop_task():

        await bot.wait_until_ready()

        while True:
            await send_verse(channel)

            await discord.utils.sleep_until(
                discord.utils.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + discord.utils.timedelta(days=1)
            )

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

    await send_verse(channel)

    await start_guild_loop(gid, channel)

    await interaction.response.send_message(
        f"✅ Daily verses will be sent in {channel.mention}",
        ephemeral=True
    )


# -----------------------------
# Startup Recovery ⭐
# -----------------------------
@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    threading.Thread(target=run_flask).start()

    config = load_config()

    for guild_id, settings in config.items():

        if not isinstance(settings, dict):
            continue

        if "channel" not in settings:
            continue

        channel = bot.get_channel(settings["channel"])

        if channel:
            bot.loop.create_task(start_guild_loop(guild_id, channel))

    print("Recovery complete")


# -----------------------------
# Run Bot
# -----------------------------
bot.run(TOKEN)
