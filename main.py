import discord
from discord import app_commands
from discord.ext import tasks
import random
import os
import json
from dotenv import load_dotenv

# =========================
# Load Token
# =========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# =========================
# Intents
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# =========================
# Config Storage
# =========================
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# Bot Setup
# =========================
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# =========================
# Verses
# =========================
verses = [
    "John 3:16 - For God so loved the world...",
    "Philippians 4:13 - I can do all things through Christ...",
    "Psalm 23:1 - The Lord is my shepherd...",
    "Romans 8:28 - And we know that in all things..."
]

# =========================
# Commands
# =========================
@bot.tree.command(name="bible", description="Select channel for daily Bible verses")
@app_commands.describe(channel="Channel to send daily verses to")
async def bible(interaction: discord.Interaction, channel: discord.TextChannel):

    config = load_config()

    guild_id = str(interaction.guild.id)
    config[guild_id] = channel.id

    save_config(config)

    await interaction.response.send_message(
        f"✅ Daily Bible verses will be sent in {channel.mention}",
        ephemeral=True
    )

# =========================
# Daily Loop
# =========================
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

        try:
            await channel.send(embed=embed)
        except:
            pass

# =========================
# Startup
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if not daily_bible.is_running():
        daily_bible.start()

# =========================
# Run Bot
# =========================
if __name__ == "__main__":
    print("Starting bot...")
    bot.run(TOKEN)
