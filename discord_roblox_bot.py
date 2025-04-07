import discord
from discord.ext import commands
import requests
import os
import re
import asyncio

# Get token securely from environment
TOKEN = os.getenv("DISCORD_TOKEN")

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent
bot = commands.Bot(command_prefix='/', intents=intents)

# Suspicious keywords
bad_words = ["predator", "grooming", "slut", "slave", "13", "furry", "rp", "daddy", "inch", "tip", "master", "czm", "bull", "snowbunny", "studio", "add for studio", "ykyk", "iykyk", "futa", "fxta", "blacked", "erp", "monster", "BBC"]

# Helper: Extract user ID and trailing number
def extract_user_id_and_number(line):
    match = re.match(r"https?://www\.roblox\.com/users/(\d+)/profile\s*-\s*(\d+)", line)
    if match:
        user_id, number = match.groups()
        return user_id, int(number)
    return None, None

# Call Roblox API to get user info
def get_user_info(user_ids):
    url = "https://users.roblox.com/v1/users"
    try:
        response = requests.post(url, json={"userIds": user_ids}, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", [])
    except requests.exceptions.RequestException:
        pass
    return []

# When bot starts
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    # Synchronize slash commands after bot is ready
    await bot.tree.sync()  # Sync global slash commands
    print("Slash commands synced!")

# /scan command
@bot.tree.command(name="scan", description="Scan Roblox profiles for suspicious activity.")
async def scan_profiles(interaction: discord.Interaction):
    await interaction.response.send_message("🔍 Scanning Roblox profiles (1–20)...")

    try:
        with open("friends.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        await interaction.response.send_message("❌ `friends.txt` not found.")
        return

    # Extract and filter
    user_ids = []
    for line in lines:
        user_id, num = extract_user_id_and_number(line)
        if user_id and num and 1 <= num <= 20:
            user_ids.append(user_id)

    flagged = []

    # Chunked API calls
    for chunk in [user_ids[i:i + 100] for i in range(0, len(user_ids), 100)]:
        users = get_user_info(chunk)
        for user in users:
            description = user.get("description", "").lower()
            found_words = [word for word in bad_words if word in description]
            if found_words:
                flagged.append((user["name"], user["id"], found_words))
        await asyncio.sleep(1.5)

    # Respond with results
    if flagged:
        await interaction.response.send_message(f"⚠️ Found {len(flagged)} suspicious profile(s):")
        for name, uid, words in flagged:
            await interaction.followup.send(f"🔸 **{name}** (ID: {uid}) | `{', '.join(words)}`\nhttps://www.roblox.com/users/{uid}/profile")
    else:
        await interaction.response.send_message("✅ No flagged profiles found.")

# /database command
@bot.tree.command(name="database", description="Show the contents of `friends.txt`.")
async def show_database(interaction: discord.Interaction):
    try:
        with open("friends.txt", "r") as f:
            friends_content = f.read()
    except FileNotFoundError:
        await interaction.response.send_message("❌ `friends.txt` not found.")
        return
    
    if friends_content.strip():
        await interaction.response.send_message(f"**Contents of friends.txt:**\n```\n{friends_content}\n```")
    else:
        await interaction.response.send_message("❌ `friends.txt` is empty.")

# Simple test ping command
@bot.tree.command(name="ping", description="Check if the bot is responsive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Start bot
bot.run(TOKEN)
