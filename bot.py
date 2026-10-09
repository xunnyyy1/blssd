"""
╔══════════════════════════════════════════════════╗
║          ANTINUKE BOT — Main Entry Point         ║
╚══════════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands
import json
import os
import logging
from colorama import Fore, Style, init

init(autoreset=True)

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.CYAN}[%(asctime)s]{Style.RESET_ALL} %(levelname)s » %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("AntiNukeBot")

# ─── Load Config ────────────────────────────────────────────────────────────
with open("config.json", "r") as f:
    config = json.load(f)

PREFIX = config.get("prefix", ",")

# ─── Intents ────────────────────────────────────────────────────────────────
intents = discord.Intents.all()

# ─── Bot Setup ──────────────────────────────────────────────────────────────
class AntiNukeBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )
        self.config = config

    async def setup_hook(self):
        """Load all cogs on startup."""
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    log.info(f"{Fore.GREEN}Loaded cog:{Style.RESET_ALL} {cog_name}")
                except Exception as e:
                    log.error(f"{Fore.RED}Failed to load {cog_name}:{Style.RESET_ALL} {e}")

    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{PREFIX}help | Protecting servers",
            )
        )
        print(
            f"\n{Fore.MAGENTA}{'═'*50}\n"
            f"  🛡️  AntiNuke Bot is ONLINE\n"
            f"  Logged in as : {self.user} (ID: {self.user.id})\n"
            f"  Prefix       : {PREFIX}\n"
            f"  Servers      : {len(self.guilds)}\n"
            f"{'═'*50}{Style.RESET_ALL}\n"
        )

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                embed=discord.Embed(
                    description="❌ You don't have permission to use this command.",
                    color=discord.Color.red(),
                )
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=discord.Embed(
                    description=f"❌ Missing argument: `{error.param.name}`",
                    color=discord.Color.orange(),
                )
            )
        else:
            log.error(f"Unhandled error: {error}")


# ─── Run ─────────────────────────────────────────────────────────────────────
bot = AntiNukeBot()

if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        log.error("No bot token set! Set the DISCORD_BOT_TOKEN environment variable.")
        exit(1)
    bot.run(token, log_handler=None)
