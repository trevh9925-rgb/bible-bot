import discord
from discord import app_commands
from discord.ext import tasks
import random
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# =============================
# LOAD TOKEN
# =============================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")

# =============================
# BOT INTENTS
# =============================
intents = discord.Intents.default()
intents.message_content = True

# =============================
# FILES
# =============================
CONFIG_FILE = "config.json"
VERSES_FILE = "nkjv_verses.json"

# =============================
# LOAD CONFIG (SAFE)
# =============================
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("Config load error:", e)
        return {}

# =============================
# SAVE CONFIG
# =============================
def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Config save error:", e)

# =============================
# LOAD VERSES (SAFE)
# =============================
def load_verses():
    if not os.path.exists(VERSES_FILE):
        return []

    try:
        with open(VERSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Verse file error:", e)
        return []

# =============================
# CREATE EMBED
# =============================
def create_verse_embed(title):

    verses = load_verses()

    if not verses:
        return None

    verse = random.choice(verses)

    book = verse.get("book")
    chapter = verse.get("chapter")
    verse_num = verse.get("verse")
    text = verse.get("text")

    embed = discord.Embed(
        title=title,
        description=text,
        color=0x2ecc71
    )

    embed.set_footer(text=f"{book} {chapter}:{verse_num} (NKJV)")

    return embed

# =============================
# RANDOM BUTTON VIEW
# =============================
class RandomVerseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Another Verse", style=discord.ButtonStyle.green)
    async def another(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = create_verse_embed("📖 Random Bible Verse")

        if embed:
            await interaction.response.edit_message(embed=embed, view=self)

# =============================
# BOT CLASS
# =============================
class BibleBot(discord.Client):

    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = BibleBot()

# =============================
# SEND VERSE
# =============================
async def send_daily_verse(channel):

    embed = create_verse_embed("📖 Daily Bible Verse")

    if embed:
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print("Send verse error:", e)

# =============================
# /bible COMMAND
# =============================
@bot.tree.command(name="bible", description="Set the channel for daily Bible verses")
@app_commands.describe(channel="Channel for daily Bible verses")

async def bible(interaction: discord.Interaction, channel: discord.TextChannel):

    config = load_config()

    guild_id = str(interaction.guild.id)

    next_send = datetime.now(timezone.utc) + timedelta(hours=24)

    config[guild_id] = {
        "channel_id": channel.id,
        "next_send": next_send.isoformat()
    }

    save_config(config)

    await send_daily_verse(channel)

    await interaction.response.send_message(
        f"✅ Daily verses will now be sent in {channel.mention}",
        ephemeral=True
    )

# =============================
# /random COMMAND
# =============================
@bot.tree.command(name="random", description="Get a random Bible verse")

async def random_verse(interaction: discord.Interaction):

    embed = create_verse_embed("📖 Random Bible Verse")

    if not embed:
        await interaction.response.send_message(
            "No verses found.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        embed=embed,
        view=RandomVerseView()
    )

# =============================
# DAILY CHECK LOOP
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

        try:
            next_send = datetime.fromisoformat(next_send_str)
        except:
            continue

        if now >= next_send:

            channel = bot.get_channel(int(channel_id))

            if channel is None:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except:
                    continue

            await send_daily_verse(channel)

            new_next = now + timedelta(hours=24)

            config[guild_id]["next_send"] = new_next.isoformat()

            updated = True

    if updated:
        save_config(config)

# =============================
# READY EVENT
# =============================
@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    if not daily_checker.is_running():
        daily_checker.start()

# =============================
# RUN BOT
# =============================
bot.run(TOKEN)
