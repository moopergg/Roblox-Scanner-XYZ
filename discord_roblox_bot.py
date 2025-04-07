import discord
from discord.ext import commands
import requests
import os
import re
import asyncio
import time

# ENV Token
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Roblox suspicious keywords
bad_words = [
    "predator", "grooming", "slut", "slave", "13", "furry", "rp", "daddy", "inch", "tip",
    "master", "czm", "bull", "snowbunny", "studio", "add for studio", "ykyk", "iykyk",
    "futa", "fxta", "blacked", "erp", "monster", "BBC"
]

# Cooldown tracking
last_rate_limit_time = 0
RATE_LIMIT_DELAY = 15  # seconds

# Active scan tasks per user
active_scans = {}

async def get_user_info(user_ids):
    global last_rate_limit_time
    url = "https://users.roblox.com/v1/users"

    # Wait if recently rate limited
    if time.time() - last_rate_limit_time < RATE_LIMIT_DELAY:
        await asyncio.sleep(RATE_LIMIT_DELAY)

    try:
        response = requests.post(url, json={"userIds": list(map(int, user_ids))}, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 429:
            last_rate_limit_time = time.time()
            print("⛔ Rate limited! Waiting 15s...")
            await asyncio.sleep(RATE_LIMIT_DELAY)
            return await get_user_info(user_ids)
    except requests.exceptions.RequestException:
        pass
    return []

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.tree.command(name="scan", description="Scan Roblox user IDs for suspicious keywords.")
async def scan(interaction: discord.Interaction, start_id: int, end_id: int):
    user_id = interaction.user.id

    # Prevent multiple scans per user
    if user_id in active_scans and not active_scans[user_id].done():
        await interaction.response.send_message("⛔ You already have an active scan running!", ephemeral=True)
        return

    await interaction.response.send_message(f"🔍 Scanning Roblox profiles from ID {start_id} to {end_id}...")

    async def do_scan():
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

        try:
            for i in range(0, len(user_ids), chunk_size):
                chunk = user_ids[i:i + chunk_size]
                await scan_chunk(chunk)
                await asyncio.sleep(0.2)  # small pacing

            if flagged:
                summary = f"⚠️ Found {len(flagged)} suspicious profile(s):\n"
                details = ""
                for name, uid, words in flagged:
                    details += f"🔸 **{name}** (ID: {uid}) | `{', '.join(words)}`\nhttps://www.roblox.com/users/{uid}/profile\n\n"
                try:
                    await interaction.user.send(summary + "\n" + details)
                    await interaction.followup.send("✅ Scan complete — results sent to your DMs.")
                except discord.Forbidden:
                    await interaction.followup.send("⚠️ Scan complete, but I couldn’t DM you.")
            else:
                await interaction.followup.send("✅ No flagged profiles found.")
        except asyncio.CancelledError:
            await interaction.followup.send("❌ Your scan was cancelled.")
        finally:
            active_scans.pop(user_id, None)

    task = asyncio.create_task(do_scan())
    active_scans[user_id] = task

@bot.tree.command(name="cancelscan", description="Cancel your currently running scan.")
async def cancelscan(interaction: discord.Interaction):
    user_id = interaction.user.id
    task = active_scans.get(user_id)
    if task and not task.done():
        task.cancel()
        await interaction.response.send_message("🛑 Your scan has been cancelled.", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ You don’t have a scan currently running.", ephemeral=True)

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

@bot.tree.command(name="ping", description="Check if the bot is responsive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

bot.run(TOKEN)
