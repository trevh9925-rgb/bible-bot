import discord
from discord import app_commands
from discord.ext import tasks
import random
import os
import json
from dotenv import load_dotenv

# =============================
# Load Token
# =============================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# =============================
# Bot Intents
# =============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# =============================
# Files
# =============================
CONFIG_FILE = "config.json"
NKJV_FILE = "nkjv_verses.json"

# =============================
# Load Config
# =============================
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =============================
# Load Verses From JSON
# =============================
def load_verses():
    if not os.path.exists(NKJV_FILE):
        return []

    try:
        with open(NKJV_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

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

# =============================
# Helper Function To Send Verse
# =============================
async def send_random_verse(channel: discord.TextChannel):
    verses_list = load_verses()

    if not verses_list:
        return

    verse_data = random.choice(verses_list)

    book = verse_data.get("book", "Unknown Book")
    chapter = verse_data.get("chapter", "?")
    verse = verse_data.get("verse", "?")
    text = verse_data.get("text", "No text available")

    verse_text = f"{book} {chapter}:{verse} - {text}"

    embed = discord.Embed(
        title="📖 Daily Bible Verse",
        description=verse_text,
        color=0x2ecc71
    )

    try:
        await channel.send(embed=embed)
    except:
        pass

# =============================
# Slash Command
# =============================
@bot.tree.command(name="bible", description="Set channel for daily Bible verses")
@app_commands.describe(channel="Channel to send daily verses")
async def bible(interaction: discord.Interaction, channel: discord.TextChannel):

    config = load_config()

    guild_id = str(interaction.guild.id)
    config[guild_id] = channel.id

    save_config(config)

    # Send immediate verse
    await send_random_verse(channel)

    await interaction.response.send_message(
        f"✅ Daily verses will now be sent in {channel.mention}",
        ephemeral=True
    )

# =============================
# Daily Loop
# =============================
@tasks.loop(hours=24)
async def daily_bible():

    await bot.wait_until_ready()

    config = load_config()

    for guild_id, channel_id in config.items():

        channel = bot.get_channel(int(channel_id))
        if not channel:
            continue

        await send_random_verse(channel)

# =============================
# Ready Event
# =============================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if not daily_bible.is_running():
        daily_bible.start()

# =============================
# Run Bot
# =============================
if __name__ == "__main__":
    bot.run(TOKEN)
