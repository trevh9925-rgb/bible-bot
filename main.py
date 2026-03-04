import discord
from discord import app_commands
from discord.ext import tasks
import random
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# =============================
# CONFIG
# =============================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

DAILY_SEND_HOUR_UTC = 12

# =============================
# FILE STORAGE
# =============================
SUB_FILE = "subscriptions.json"
NKJV_FILE = "nkjv_verses.json"

# =============================
# INTENTS
# =============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# =============================
# STORAGE HELPERS
# =============================
def load_subs():
    if not os.path.exists(SUB_FILE):
        return {}
    try:
        with open(SUB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_subs(data):
    with open(SUB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_verses():
    if not os.path.exists(NKJV_FILE):
        return []
    try:
        with open(NKJV_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# =============================
# EMBED BUILDER
# =============================
def create_verse_embed(title):

    verses = load_verses()
    if not verses:
        return None

    verse = random.choice(verses)

    book = verse.get("book", "Unknown Book")
    chapter = verse.get("chapter", "?")
    verse_num = verse.get("verse", "?")
    text = verse.get("text", "No text available")

    embed = discord.Embed(
        title=title,
        description=text,
        color=0x2ecc71
    )

    embed.set_footer(text=f"{book} {chapter}:{verse_num} (NKJV)")
    return embed

# =============================
# BUTTON VIEW
# =============================
class RandomVerseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Get Another Verse",
        style=discord.ButtonStyle.green
    )
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = create_verse_embed("📖 Random Bible Verse")

        if embed:
            await interaction.response.edit_message(
                embed=embed,
                view=self
            )

# =============================
# BOT CLASS
# =============================
class MyBot(discord.Client):

    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        print("Syncing commands...")
        await self.tree.sync()
        print("Commands synced.")

bot = MyBot()

# =============================
# BROADCAST FUNCTION
# =============================
async def broadcast_daily_verse():

    verses = load_verses()
    if not verses:
        return

    verse = random.choice(verses)

    book = verse.get("book", "Unknown Book")
    chapter = verse.get("chapter", "?")
    verse_num = verse.get("verse", "?")
    text = verse.get("text", "No text available")

    embed = discord.Embed(
        title="📖 Daily Bible Verse",
        description=text,
        color=0x2ecc71
    )

    embed.set_footer(text=f"{book} {chapter}:{verse_num} (NKJV)")

    subs = load_subs()

    for guild_id, data in subs.items():

        channel_id = data.get("channel_id")
        if not channel_id:
            continue

        channel = bot.get_channel(int(channel_id))

        if channel:
            try:
                await channel.send(embed=embed, view=RandomVerseView())
            except:
                pass

# =============================
# AUTO RECOVERY DAILY LOOP
# =============================
@tasks.loop(seconds=30)
async def daily_checker():

    await bot.wait_until_ready()

    now = datetime.now(timezone.utc)

    # Broadcast once per hour/minute match
    if now.hour == DAILY_SEND_HOUR_UTC and now.minute == 0:

        print("Sending daily devotional broadcast...")

        try:
            await broadcast_daily_verse()

            # Prevent duplicate sending
            await discord.utils.sleep_until(
                now + timedelta(seconds=61)
            )

        except Exception as e:
            print(f"Broadcast error: {e}")

# =============================
# ON READY (AUTO RESUB RECOVERY)
# =============================
@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    # Validate subscriptions
    try:
        subs = load_subs()
        valid_subs = {}

        for guild_id, data in subs.items():

            channel = bot.get_channel(int(data["channel_id"]))

            if channel:
                valid_subs[guild_id] = data
            else:
                print(f"Removed invalid subscription: {guild_id}")

        save_subs(valid_subs)

        print("Subscription recovery completed.")

    except Exception as e:
        print(f"Recovery error: {e}")

    if not daily_checker.is_running():
        daily_checker.start()

    print("Bot is ready.")

# =============================
# /bible COMMAND
# =============================
@bot.tree.command(
    name="bible",
    description="Subscribe a channel to daily Bible verses"
)
@app_commands.describe(channel="Channel to send daily verses")
async def bible(interaction: discord.Interaction, channel: discord.TextChannel):

    subs = load_subs()

    subs[str(interaction.guild.id)] = {
        "channel_id": channel.id
    }

    save_subs(subs)

    # Instant verse send
    embed = create_verse_embed("📖 Daily Bible Verse")

    if embed:
        await channel.send(embed=embed, view=RandomVerseView())

    await interaction.response.send_message(
        f"✅ Subscribed daily verses to {channel.mention}",
        ephemeral=True
    )

# =============================
# /random COMMAND
# =============================
@bot.tree.command(
    name="random",
    description="Get a random Bible verse"
)
async def random_verse(interaction: discord.Interaction):

    embed = create_verse_embed("📖 Random Bible Verse")

    if not embed:
        await interaction.response.send_message(
            "No verses available.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        embed=embed,
        view=RandomVerseView()
    )

# =============================
# RUN BOT
# =============================
if __name__ == "__main__":
    bot.run(TOKEN)
