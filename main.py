import discord
from discord import app_commands
from discord.ext import tasks
import random
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

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
# Load / Save Config
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
# Load Verses
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
# Create Verse Embed
# =============================
def create_verse_embed(title="📖 Bible Verse"):
    verses_list = load_verses()

    if not verses_list:
        return None

    verse_data = random.choice(verses_list)

    book = verse_data.get("book", "Unknown Book")
    chapter = verse_data.get("chapter", "?")
    verse = verse_data.get("verse", "?")
    text = verse_data.get("text", "No text available")

    embed = discord.Embed(
        title=title,
        description=text,
        color=0x2ecc71
    )

    embed.set_footer(text=f"{book} {chapter}:{verse} (NKJV)")

    return embed

# =============================
# Button View For Random Verse
# =============================
class RandomVerseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Another Verse", style=discord.ButtonStyle.green)
    async def another_verse(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_verse_embed("📖 Random Bible Verse")
        if embed:
            await interaction.response.edit_message(embed=embed, view=self)

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
# Send Verse To Channel (Daily)
# =============================
async def send_random_verse(channel: discord.TextChannel):
    embed = create_verse_embed("📖 Daily Bible Verse")
    if embed:
        try:
            await channel.send(embed=embed)
        except:
            pass

# =============================
# Slash Command - Set Daily Channel
# =============================
@bot.tree.command(name="bible", description="Set channel for daily Bible verses")
@app_commands.describe(channel="Channel to send daily verses")
async def bible(interaction: discord.Interaction, channel: discord.TextChannel):

    config = load_config()
    guild_id = str(interaction.guild.id)

    next_send = datetime.now(timezone.utc) + timedelta(hours=24)

    config[guild_id] = {
        "channel_id": channel.id,
        "next_send": next_send.isoformat()
    }

    save_config(config)

    await send_random_verse(channel)

    await interaction.response.send_message(
        f"✅ Daily verses will now be sent in {channel.mention}",
        ephemeral=True
    )

# =============================
# Slash Command - Random Verse
# =============================
@bot.tree.command(name="random", description="Get a random Bible verse instantly")
async def random_verse(interaction: discord.Interaction):

    embed = create_verse_embed("📖 Random Bible Verse")

    if not embed:
        await interaction.response.send_message(
            "❌ No verses found in nkjv_verses.json.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        embed=embed,
        view=RandomVerseView()
    )

# =============================
# Persistent Daily Checker
# =============================
@tasks.loop(minutes=5)
async def daily_checker():

    await bot.wait_until_ready()

    config = load_config()
    now = datetime.now(timezone.utc)

    updated = False

    for guild_id, data in config.items():

        channel_id = data.get("channel_id")
        next_send_str = data.get("next_send")

        if not channel_id or not next_send_str:
            continue

        next_send = datetime.fromisoformat(next_send_str)

        if now >= next_send:

            channel = bot.get_channel(int(channel_id))
            if channel:
                await send_random_verse(channel)

            new_next_send = now + timedelta(hours=24)
            config[guild_id]["next_send"] = new_next_send.isoformat()
            updated = True

    if updated:
        save_config(config)

# =============================
# Ready Event
# =============================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if not daily_checker.is_running():
        daily_checker.start()

# =============================
# Run Bot
# =============================
if __name__ == "__main__":
    bot.run(TOKEN)
