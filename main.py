import discord
from discord import app_commands
from discord.ext import tasks
import random
import os
import json
import time
import threading
import asyncio
from dotenv import load_dotenv
from flask import Flask

# =============================
# Load Token
# =============================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# =============================
# Flask Heartbeat Server
# =============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bible Bot Running"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# =============================
# Config System
# =============================
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =============================
# Bot Setup
# =============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# =============================
# Verses
# =============================
verses = [
    "John 3:16 - For God so loved the world...",
    "Philippians 4:13 - I can do all things through Christ...",
    "Psalm 23:1 - The Lord is my shepherd...",
    "Romans 8:28 - And we know that in all things..."
]

# =============================
# Commands
# =============================
@bot.tree.command(name="bible", description="Select Bible verse channel")
@app_commands.describe(channel="Channel for daily verses")
async def bible(interaction: discord.Interaction, channel: discord.TextChannel):

    config = load_config()

    guild_id = str(interaction.guild.id)
    config[guild_id] = channel.id

    save_config(config)

    await interaction.response.send_message(
        f"✅ Daily Bible verses will now be sent in {channel.mention}",
        ephemeral=True
    )

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
            description=verse,
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
# Safe Render Login Loop
# (Prevents 429 Rate Limit Login Spam)
# =============================
async def safe_start():
    while True:
        try:
            await bot.start(TOKEN)
        except Exception as e:
            print(f"Bot restart after error: {e}")
            await asyncio.sleep(60)

# =============================
# Main Startup
# =============================
if __name__ == "__main__":

    threading.Thread(target=run_flask).start()

    time.sleep(random.randint(5, 15))

    asyncio.run(safe_start())
