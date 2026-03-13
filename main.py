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

# =============================
# BOT INTENTS
# =============================
intents = discord.Intents.default()
intents.message_content = True

# =============================
# FILES
# =============================
SUB_FILE = "subscriptions.json"
VERSES_FILE = "nkjv_verses.json"

# =============================
# DAILY LOCK
# =============================
last_sent_date = None

# =============================
# LOAD SUBSCRIPTIONS
# =============================
def load_subscriptions():

    if not os.path.exists(SUB_FILE):
        with open(SUB_FILE, "w") as f:
            json.dump({}, f)
        return {}

    try:
        with open(SUB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

# =============================
# SAVE SUBSCRIPTIONS
# =============================
def save_subscriptions(data):
    with open(SUB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =============================
# LOAD VERSES
# =============================
def load_verses():

    if not os.path.exists(VERSES_FILE):
        return []

    try:
        with open(VERSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# =============================
# CREATE VERSE EMBED
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
# SEND DAILY VERSE
# =============================
async def send_daily_verse(channel):

    embed = create_verse_embed("📖 Daily Bible Verse")

    if embed:
        try:
            await channel.send(embed=embed)
        except:
            pass

# =============================
# /bible COMMAND
# =============================
@bot.tree.command(name="bible", description="Set the channel for daily Bible verses")
@app_commands.describe(channel="Channel for daily Bible verses")

async def bible(interaction: discord.Interaction, channel: discord.TextChannel):

    subs = load_subscriptions()

    guild_id = str(interaction.guild.id)

    subs[guild_id] = {
        "channel_id": channel.id
    }

    save_subscriptions(subs)

    # Send verse immediately
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
@tasks.loop(minutes=1)
async def daily_checker():

    global last_sent_date

    await bot.wait_until_ready()

    subs = load_subscriptions()

    now = datetime.now(timezone.utc)

    # Convert to JST
    jst = now + timedelta(hours=9)

    # Send at 9 PM JST
    if jst.hour == 21 and jst.minute == 0:

        today = jst.date()

        # Prevent duplicate sends
        if last_sent_date == today:
            return

        last_sent_date = today

        for guild_id, data in subs.items():

            channel_id = data.get("channel_id")

            if not channel_id:
                continue

            channel = bot.get_channel(int(channel_id))

            if channel is None:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except:
                    continue

            await send_daily_verse(channel)

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
