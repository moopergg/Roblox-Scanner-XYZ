import discord
from discord.ext import commands
import requests
import os
import re
import asyncio

# Get bot token from environment
TOKEN = os.getenv("DISCORD_TOKEN")

# Discord intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix="/", intents=intents)

# Suspicious keywords
bad_words = [
    "predator", "grooming", "slut", "slave", "13", "furry", "rp", "daddy", "inch", "tip",
    "master", "czm", "bull", "snowbunny", "studio", "add for studio", "ykyk", "iykyk",
    "futa", "fxta", "blacked", "erp", "monster", "BBC"
]

# Helper: fetch user info from Roblox API
async def get_user_info(user_ids):
    url = "https://users.roblox.com/v1/users"
    try:
        response = requests.post(url, json={"userIds": list(map(int, user_ids))}, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 429:
            await asyncio.sleep(5)
            return await get_user_info(user_ids)
    except requests.exceptions.RequestException:
        pass
    return []

# Bot is ready
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# /scan command
@bot.tree.command(name="scan", description="Scan Roblox user IDs for suspicious keywords.")
async def scan(interaction: discord.Interaction, start_id: int, end_id: int):
    await interaction.response.send_message(f"🔍 Scanning Roblox profiles from ID {start_id} to {end_id}...")

    user_ids = [str(i) for i in range(start_id, end_id + 1)]
    flagged = []
    chunk_size = 20

    async def scan_chunk(chunk):
        users = await get_user_info(chunk)
        for user in users:
            description = user.get("description", "").lower()
            matches = [w for w in bad_words if w in description]
            if matches:
                flagged.append((user["name"], user["id"], matches))

    tasks = [scan_chunk(user_ids[i:i + chunk_size]) for i in range(0, len(user_ids), chunk_size)]
    await asyncio.gather(*tasks)

    if flagged:
        summary = f"⚠️ Found {len(flagged)} suspicious profile(s):\n"
        details = ""
        for name, uid, words in flagged:
            details += f"🔸 **{name}** (ID: {uid}) | `{', '.join(words)}`\nhttps://www.roblox.com/users/{uid}/profile\n\n"
        try:
            await interaction.user.send(summary + "\n" + details)
            await interaction.followup.send("✅ Scan complete — results have been sent to your DMs.")
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Scan complete, but I couldn’t DM you. Please enable DMs from server members.")
    else:
        await interaction.followup.send("✅ No flagged profiles found.")

# /database command
@bot.tree.command(name="database", description="Show the contents of friends.txt.")
async def show_database(interaction: discord.Interaction):
    try:
        if not os.path.exists("friends.txt"):
            await interaction.response.send_message("❌ `friends.txt` not found.")
            return

        with open("friends.txt", "r") as f:
            content = f.read()

        preview = content[:1000]
        await interaction.response.send_message(
            f"📄 Preview of `friends.txt` (first 1000 characters):\n```\n{preview}\n```"
        )
        await interaction.followup.send(file=discord.File("friends.txt"))

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}")

# /ping command
@bot.tree.command(name="ping", description="Check if the bot is responsive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

# Run the bot
bot.run(TOKEN)
