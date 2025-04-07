import discord
from discord.ext import commands
import requests
import os
import re
import asyncio

from keep_alive import keep_alive # NEW

# Get token securely from environment
TOKEN = os.getenv("DISCORD_TOKEN")

keep_alive() # NEW

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

# /scan command
@bot.command(name="scan")
async def scan_profiles(ctx):
    await ctx.send("🔍 Scanning Roblox profiles (1–20)...")

    try:
        with open("friends.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        await ctx.send("❌ `friends.txt` not found.")
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
        await ctx.send(f"⚠️ Found {len(flagged)} suspicious profile(s):")
        for name, uid, words in flagged:
            await ctx.send(f"🔸 **{name}** (ID: {uid}) | `{', '.join(words)}`\nhttps://www.roblox.com/users/{uid}/profile")
    else:
        await ctx.send("✅ No flagged profiles found.")

# /database command
@bot.command(name="database")
async def show_database(ctx):
    """Shows the contents of friends.txt."""
    try:
        with open("friends.txt", "r") as f:
            friends_content = f.read()
    except FileNotFoundError:
        await ctx.send("❌ `friends.txt` not found.")
        return
    
    if friends_content.strip():
        await ctx.send(f"**Contents of friends.txt:**\n```\n{friends_content}\n```")
    else:
        await ctx.send("❌ `friends.txt` is empty.")

# Simple test ping command
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

# Start bot
bot.run(TOKEN)
