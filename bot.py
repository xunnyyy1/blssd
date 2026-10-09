"""
╔══════════════════════════════════════════════════╗
║          ANTINUKE BOT — Main Entry Point         ║
╚══════════════════════════════════════════════════╝
"""
import discord
from discord.ext import commands
import json
import os
import sys
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, "config.json")
config = {}
if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        log.warning(f"Failed to read config.json: {e}")

PREFIX = config.get("prefix", ",")
# ─── Lightweight Web Server for Render / Cloud Hosting ─────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"AntiNuke Bot is online and running!")
    def log_message(self, format, *args):
        # Silence HTTP access logs to keep console clean
        return
def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        log.info(f"{Fore.GREEN}Health check server running on port {port}{Style.RESET_ALL}")
        server.serve_forever()
    except Exception as e:
        log.warning(f"Web server could not start on port {port}: {e}")
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
        cogs_dir = os.path.join(BASE_DIR, "cogs")
        if os.path.exists(cogs_dir):
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
    # Start web server in background thread for Render
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    # Search for token across environment variables and config.json
    token = (
        os.environ.get("DISCORD_BOT_TOKEN")
        or os.environ.get("TOKEN")
        or os.environ.get("DISCORD_TOKEN")
        or os.environ.get("BOT_TOKEN")
        or config.get("token")
        or ""
    ).strip()
    if not token or token == "MTU1ODAwMjQ1ODU2NTkzOTI2MQ.GmSYLi.tQ3u2YqF1GfNDiAKxdS-hB3D_mO82bakutjpvU":
        log.error("No bot token found! Please put your token in config.json or set the TOKEN environment variable in Render.")
        sys.exit(1)
    bot.run(token, log_handler=None)
