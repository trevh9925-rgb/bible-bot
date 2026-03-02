import discord
from discord.ext import tasks
from discord import app_commands
import random
import json
import os
import time
import threading
from dotenv import load_dotenv
from flask import Flask

# =============================
# Load Token
# =============================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# =============================
# Flask Heartbeat Server (Render)
# =============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bible Bot Running"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# =============================
# Bot Setup
# =============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

CONFIG_FILE = "config.json"
VERSE_FILE = "nkjv_verses.json"

# =============================
# File Loaders
# =============================
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_verses():
    with open(VERSE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# =============================
# Bot Class
# =============================
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()
verses = load_verses()

# =============================
# Commands
# =============================
@bot.tree.command(name="bible", description="Select daily Bible verse channel")
@app_commands.describe(channel="Channel to send daily verses")
async def bible(interaction: discord.Interaction, channel: discord.TextChannel):

    config = load_config()

    guild_id = str(interaction.guild.id)
    config[guild_id] = channel.id

    save_config(config)

    await interaction.response.send_message(
        f"✅ Daily Bible verses will be sent in {channel.mention}",
        ephemeral=True
    )

    # Send immediate verse
    verse = random.choice(verses)

    embed = discord.Embed(
        title="📖 Daily Bible Verse",
        description=f"**{verse['book']} {verse['chapter']}:{verse['verse']}**\n\n{verse['text']}",
        color=0x2ecc71
    )

    await channel.send(embed=embed)

# =============================
# Daily Verse Loop
# =============================
@tasks.loop(hours=24)
async def daily_bible():

    await bot.wait_until_ready()

    config = load_config()

    for guild_id, channel_id in config.items():

        channel = bot.get_channel(int(channel_id))
        if not channel:
            continue

        verse = random.choice(verses)

        embed = discord.Embed(
            title="📖 Daily Bible Verse",
            description=f"**{verse['book']} {verse['chapter']}:{verse['verse']}**\n\n{verse['text']}",
            color=0x2ecc71
        )

        await channel.send(embed=embed)

# =============================
# Ready Event
# =============================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if not daily_bible.is_running():
        daily_bible.start()

# =============================
# Startup (Render Safe)
# =============================
if __name__ == "__main__":

    # Start Flask heartbeat
    threading.Thread(target=run_flask).start()

    # Random startup delay to avoid rate limit bursts
    time.sleep(random.randint(10, 30))

    print("Starting Discord bot...")

    bot.run(TOKEN)
