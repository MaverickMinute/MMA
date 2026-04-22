import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

async def main():
    async with bot:
        await bot.load_extension("cogs.moderation")
        await bot.start(os.getenv("TOKEN"))

GUILD_ID = 1496324891438223370  # <-- put your server ID here

@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)

    # THIS LINE registers slash commands instantly in YOUR server
    await bot.tree.sync(guild=guild)

    print(f"Logged in as {bot.user}")
    print("Slash commands synced to guild.")
asyncio.run(main())