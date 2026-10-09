"""
╔══════════════════════════════════════════════════╗
║         TOOLS COG — Multi-Tools Commands         ║
╚══════════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands
import instaloader
import asyncio
import logging
import sys
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# Icon loader (custom Discord emoji icons with Unicode fallback)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from icons import e

log = logging.getLogger("Tools")
_executor = ThreadPoolExecutor(max_workers=3)

# ── Colour palette ─────────────────────────────────────────────────────────
PINK    = 0xE1306C
BLURPLE = 0x5865F2
GREEN   = 0x57F287
RED     = 0xED4245
ORANGE  = 0xFEA800
DARK    = 0x2B2D31


def _fmt(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return f"{n:,}"


def _fetch_instagram_profile(username: str) -> dict:
    L = instaloader.Instaloader(
        download_pictures=False, download_videos=False,
        download_video_thumbnails=False, download_geotags=False,
        download_comments=False, save_metadata=False,
        compress_json=False, quiet=True,
    )
    p = instaloader.Profile.from_username(L.context, username)
    return {
        "username":        p.username,
        "full_name":       p.full_name or "N/A",
        "biography":       p.biography or "",
        "followers":       p.followers,
        "following":       p.followees,
        "posts":           p.mediacount,
        "is_private":      p.is_private,
        "is_verified":     p.is_verified,
        "profile_pic_url": p.profile_pic_url,
        "external_url":    p.external_url or "",
        "url":             f"https://instagram.com/{p.username}",
    }


class Tools(commands.Cog):
    """🔧 Multi-purpose utility tools."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─────────────────────────────────────────────────────────────
    # ,help
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="help", aliases=["h", "cmds", "commands"])
    async def help_cmd(self, ctx: commands.Context):
        p = self.bot.command_prefix

        embed = discord.Embed(
            description=(
                "```\n"
                "  ╔══════════════════════════════╗\n"
                "  ║      ANTINUKE  BOT  v1.0      ║\n"
                "  ╚══════════════════════════════╝\n"
                "```"
                f"> Your all-in-one server protection & utility bot.\n"
                f"> Prefix: **`{p}`**"
            ),
            color=BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=f"{self.bot.user.name}  ·  Command Menu",
            icon_url=self.bot.user.display_avatar.url,
        )
        if ctx.guild and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        embed.add_field(
            name=f"{e('shield')}  Anti‑Nuke",
            value=(
                f"`{p}antinuke`  ·  Control panel\n"
                f"`{p}antinuke toggle`  ·  Enable / Disable\n"
                f"`{p}antinuke wl add @user`  ·  Whitelist\n"
                f"`{p}antinuke wl remove @user`\n"
                f"`{p}antinuke punishment <ban|kick|strip>`"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"{e('instagram')}  Social",
            value=(
                f"`{p}ins <username>`  ·  Instagram lookup\n"
                f"*e.g.* `{p}ins @echo_sanfordd`"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"{e('globe')}  Utility",
            value=(
                f"`{p}invite`  ·  Bot invite link\n"
                f"`{p}serverinfo`  ·  Full server card\n"
                f"`{p}userinfo [@user]`  ·  User card\n"
                f"`{p}avatar [@user]`  ·  High-res avatar\n"
                f"`{p}banner [@user]`  ·  Profile / server banner\n"
                f"`{p}ping`  ·  Latency check"
            ),
            inline=False,
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}  ·  {len(self.bot.commands)} commands",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────
    # ,invite
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="invite", aliases=["inv", "addbot", "link"])
    async def invite_cmd(self, ctx: commands.Context):
        """Send the bot's invite link."""
        invite_url = self.bot.config.get(
            "invite_url",
            f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot",
        )

        embed = discord.Embed(
            description=(
                "```\n"
                "  ╔══════════════════════════════╗\n"
                "  ║     Invite AntiNuke Bot       ║\n"
                "  ╚══════════════════════════════╝\n"
                "```"
                f"> Click the button below to add **{self.bot.user.name}** to your server.\n"
                f"> Requires **Administrator** permission to function correctly."
            ),
            color=BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=f"{self.bot.user.name}  ·  Invite",
            icon_url=self.bot.user.display_avatar.url,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name=f"{e('link')}  Invite Link",
            value=f"**[» Click here to invite the bot «]({invite_url})**",
            inline=False,
        )
        embed.add_field(
            name=f"{e('shield')}  What's included",
            value=(
                f"{e('shield')}  Anti-Nuke Protection\n"
                f"{e('warning')}  Anti-Spam System\n"
                f"{e('bot')}  Unauthorized Bot Detection\n"
                f"{e('instagram')}  Instagram Lookup\n"
                f"{e('globe')}  Server & User Info"
            ),
            inline=False,
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}  ·  antinukebot by kold",
            icon_url=ctx.author.display_avatar.url,
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Invite Bot",
            style=discord.ButtonStyle.link,
            url=invite_url,
            emoji="🔗",
        ))

        await ctx.send(embed=embed, view=view)

    # ─────────────────────────────────────────────────────────────
    # ,ins — Instagram Lookup
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="ins", aliases=["instagram", "ig"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def instagram_lookup(self, ctx: commands.Context, *, username: str):
        username = username.strip().lstrip("@").split()[0]

        loading = discord.Embed(
            description=f"{e('loading')}  Fetching **@{username}**…",
            color=PINK,
        )
        loading.set_author(
            name="Instagram  ·  Lookup",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Instagram_icon.png/600px-Instagram_icon.png",
        )
        msg = await ctx.send(embed=loading)

        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(_executor, _fetch_instagram_profile, username)
        except instaloader.exceptions.ProfileNotExistsException:
            await msg.edit(embed=discord.Embed(
                title=f"{e('error')}  Profile Not Found",
                description=f"> No account found for **@{username}**.",
                color=RED,
            ))
            return
        except instaloader.exceptions.ConnectionException as ex:
            await msg.edit(embed=discord.Embed(
                title=f"{e('error')}  Connection Error",
                description=f"> Instagram may be rate-limiting.\n> Try again in a few minutes.\n```{ex}```",
                color=RED,
            ))
            return
        except Exception as ex:
            await msg.edit(embed=discord.Embed(
                title=f"{e('error')}  Unexpected Error",
                description=f"```{ex}```",
                color=RED,
            ))
            log.error(f"Instagram error for {username}: {ex}")
            return

        # ── Status badges ─────────────────────────────────
        status  = f"{e('verified')} Verified  " if data["is_verified"] else ""
        privacy = f"{e('private')} Private"    if data["is_private"]  else f"{e('globe')} Public"
        bio     = (data["biography"][:253] + "…") if len(data["biography"]) > 256 else data["biography"]

        embed = discord.Embed(
            url=data["url"],
            description=(
                f"**{status}{privacy}**\n\n"
                + (f"*{bio}*\n\n" if bio else "")
                + (f"{e('link')} [{data['external_url']}]({data['external_url']})" if data["external_url"] else "")
            ),
            color=PINK,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=f"{data['full_name']}  (@{data['username']})",
            url=data["url"],
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Instagram_icon.png/600px-Instagram_icon.png",
        )
        embed.set_thumbnail(url=data["profile_pic_url"])

        # ── Stats ─────────────────────────────────────────
        embed.add_field(
            name=f"{e('followers')}  Followers",
            value=f"```{_fmt(data['followers'])}```",
            inline=True,
        )
        embed.add_field(
            name=f"{e('following')}  Following",
            value=f"```{_fmt(data['following'])}```",
            inline=True,
        )
        embed.add_field(
            name=f"{e('posts')}  Posts",
            value=f"```{_fmt(data['posts'])}```",
            inline=True,
        )
        embed.add_field(
            name=f"{e('link')}  Profile",
            value=f"[instagram.com/{data['username']}]({data['url']})",
            inline=False,
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}  ·  instagram.com",
            icon_url=ctx.author.display_avatar.url,
        )
        await msg.edit(embed=embed)

    @instagram_lookup.error
    async def instagram_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                embed=discord.Embed(
                    description=f"{e('warning')}  Slow down! Try again in `{error.retry_after:.1f}s`.",
                    color=ORANGE,
                ),
                delete_after=5,
            )

    # ─────────────────────────────────────────────────────────────
    # ,ping
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        ms = round(self.bot.latency * 1000)

        if   ms < 80:   color, icon, bar, label = GREEN,  e("ping_great"), f"{e('ping_great')}{e('ping_great')}{e('ping_great')}{e('ping_great')}{e('ping_great')}", "Excellent"
        elif ms < 150:  color, icon, bar, label = GREEN,  e("ping_good"),  f"{e('ping_good')}{e('ping_good')}{e('ping_good')}{e('ping_good')}▪️", "Good"
        elif ms < 250:  color, icon, bar, label = ORANGE, e("ping_avg"),   f"{e('ping_avg')}{e('ping_avg')}{e('ping_avg')}▪️▪️", "Average"
        elif ms < 400:  color, icon, bar, label = ORANGE, e("ping_bad"),   f"{e('ping_bad')}{e('ping_bad')}▪️▪️▪️", "High"
        else:           color, icon, bar, label = RED,    e("ping_dead"),  f"{e('ping_dead')}▪️▪️▪️▪️", "Very High"

        embed = discord.Embed(
            title=f"{e('latency')}  Pong!",
            description=(
                f"```\n"
                f"  Latency  :  {ms}ms\n"
                f"  Status   :  {label}\n"
                f"```"
                f"{bar}"
            ),
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name="Network Latency", icon_url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────
    # ,userinfo
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="userinfo", aliases=["whois", "ui"])
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        roles = [r.mention for r in reversed(member.roles) if r != ctx.guild.default_role]

        created_ts = int(member.created_at.timestamp())
        joined_ts  = int(member.joined_at.timestamp()) if member.joined_at else None

        status_map = {
            discord.Status.online:  (e("online"),  "Online"),
            discord.Status.idle:    (e("dot_orange"), "Idle"),
            discord.Status.dnd:     (e("dot_red"), "Do Not Disturb"),
            discord.Status.offline: (e("offline"), "Offline"),
        }
        s_icon, s_label = status_map.get(member.status, (e("offline"), "Offline"))

        color = member.color if str(member.color) != "#000000" else BLURPLE

        embed = discord.Embed(
            description=(
                f"{s_icon} **{s_label}**"
                + (f"  ·  Nick: `{member.nick}`" if member.nick else "")
            ),
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=f"{member}  ·  User Info",
            icon_url=member.display_avatar.url,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        # ── Identity ──────────────────────────────────────
        embed.add_field(
            name=f"{e('id')}  Identity",
            value=(
                f"**ID** `{member.id}`\n"
                f"**Bot** `{'Yes' if member.bot else 'No'}`\n"
                f"**Top Role** {member.top_role.mention}"
            ),
            inline=True,
        )

        # ── Dates ─────────────────────────────────────────
        embed.add_field(
            name=f"{e('calendar')}  Dates",
            value=(
                f"**Created** <t:{created_ts}:D>\n"
                f"<t:{created_ts}:R>\n"
                f"**Joined** " + (f"<t:{joined_ts}:D>\n<t:{joined_ts}:R>" if joined_ts else "Unknown")
            ),
            inline=True,
        )

        # ── Badges ────────────────────────────────────────
        flags_list = []
        if member.premium_since:
            flags_list.append(f"{e('boost')} Boosting since <t:{int(member.premium_since.timestamp())}:R>")
        pf = member.public_flags
        if pf.staff:            flags_list.append(f"{e('badge')} Discord Staff")
        if pf.partner:          flags_list.append(f"{e('badge')} Partnered")
        if pf.bug_hunter:       flags_list.append(f"{e('badge')} Bug Hunter")
        if pf.early_supporter:  flags_list.append(f"{e('badge')} Early Supporter")
        if pf.verified_bot:     flags_list.append(f"{e('verified')} Verified Bot")
        if flags_list:
            embed.add_field(
                name=f"{e('badge')}  Badges",
                value="\n".join(flags_list),
                inline=False,
            )

        # ── Roles ─────────────────────────────────────────
        if roles:
            rs = "  ".join(roles[:12]) + (f"  *+{len(roles)-12} more*" if len(roles) > 12 else "")
            embed.add_field(name=f"{e('role')}  Roles [{len(roles)}]", value=rs, inline=False)
        else:
            embed.add_field(name=f"{e('role')}  Roles", value="`No roles`", inline=False)

        # ── User banner ───────────────────────────────────
        try:
            fetched = await self.bot.fetch_user(member.id)
            if fetched.banner:
                embed.set_image(url=fetched.banner.url)
                embed.add_field(name=f"{e('banner')}  Banner", value="*shown below*", inline=False)
        except Exception:
            pass

        embed.set_footer(
            text=f"Requested by {ctx.author}  ·  {ctx.guild.name}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────
    # ,serverinfo
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="serverinfo", aliases=["si", "server", "guild"])
    async def serverinfo(self, ctx: commands.Context):
        guild   = ctx.guild
        total   = guild.member_count
        bots    = sum(1 for m in guild.members if m.bot)
        humans  = total - bots
        online  = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)

        created_ts = int(guild.created_at.timestamp())
        owner = guild.owner

        vl_map = {
            discord.VerificationLevel.none:    f"{e('dot_green')} None",
            discord.VerificationLevel.low:     f"{e('dot_green')} Low",
            discord.VerificationLevel.medium:  f"{e('dot_orange')} Medium",
            discord.VerificationLevel.high:    f"{e('dot_red')} High",
            discord.VerificationLevel.highest: f"{e('dot_red')} Highest",
        }
        vl = vl_map.get(guild.verification_level, str(guild.verification_level))

        tier    = guild.premium_tier
        boosts  = guild.premium_subscription_count
        tier_icons = {0: "▪️▪️▪️", 1: f"{e('boost')}▪️▪️", 2: f"{e('boost')}{e('boost')}▪️", 3: f"{e('boost')}{e('boost')}{e('boost')}"}
        tier_bar   = tier_icons.get(tier, "▪️▪️▪️")
        boost_next = (
            f"Need `{2 - boosts}` more for Lv 1"  if tier == 0 and boosts < 2  else
            f"Need `{15 - boosts}` more for Lv 2" if tier == 1 and boosts < 15 else
            f"Need `{30 - boosts}` more for Lv 3" if tier == 2 and boosts < 30 else
            "**Max Level 🎉**"
        )

        embed = discord.Embed(
            description=(
                f"> {e('id')}  **ID** `{guild.id}`\n"
                f"> {e('owner')}  **Owner** {owner.mention if owner else 'Unknown'}\n"
                f"> {e('calendar')}  **Created** <t:{created_ts}:D>  (<t:{created_ts}:R>)"
            ),
            color=BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=f"{guild.name}  ·  Server Info",
            icon_url=guild.icon.url if guild.icon else discord.Embed.Empty,
        )

        # ── Server icon ───────────────────────────────────
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.with_size(512).url)

        # ── Members ───────────────────────────────────────
        embed.add_field(
            name=f"{e('members')}  Members",
            value=(
                f"{e('members')}  Humans  `{humans:,}`\n"
                f"{e('bot')}  Bots  `{bots:,}`\n"
                f"{e('online')}  Online  `{online:,}`\n"
                f"{e('dot_gray')}  Total  `{total:,}`"
            ),
            inline=True,
        )

        # ── Channels ──────────────────────────────────────
        embed.add_field(
            name=f"{e('text_channel')}  Channels",
            value=(
                f"{e('text_channel')}  Text  `{len(guild.text_channels)}`\n"
                f"{e('voice_channel')}  Voice  `{len(guild.voice_channels)}`\n"
                f"{e('category')}  Cats  `{len(guild.categories)}`\n"
                f"{e('thread')}  Threads  `{len(guild.threads)}`"
            ),
            inline=True,
        )

        # ── Stats ─────────────────────────────────────────
        embed.add_field(
            name=f"{e('role')}  Stats",
            value=(
                f"{e('role')}  Roles  `{len(guild.roles)}`\n"
                f"{e('emoji_icon')}  Emojis  `{len(guild.emojis)}`\n"
                f"{e('sticker')}  Stickers  `{len(guild.stickers)}`\n"
                f"{e('shield')}  Verify  {vl}"
            ),
            inline=True,
        )

        # ── Boosts ────────────────────────────────────────
        embed.add_field(
            name=f"{e('boost')}  Nitro Boosts",
            value=(
                f"{tier_bar}  **Level {tier}**  ·  `{boosts}` boosts\n"
                f"{boost_next}"
            ),
            inline=False,
        )

        # ── Server Features ───────────────────────────────
        feat_map = {
            "VERIFIED":    f"{e('verified')} Verified",
            "PARTNERED":   f"{e('badge')} Partnered",
            "COMMUNITY":   f"{e('globe')} Community",
            "DISCOVERABLE":f"{e('globe')} Discoverable",
            "ANIMATED_ICON":f"{e('avatar')} Animated Icon",
            "BANNER":      f"{e('banner')} Server Banner",
            "INVITE_SPLASH":f"{e('banner')} Invite Splash",
            "NEWS":        f"{e('text_channel')} Announcements",
        }
        if guild.vanity_url_code:
            feat_map["VANITY_URL"] = f"{e('link')} discord.gg/{guild.vanity_url_code}"

        active = [feat_map[f] for f in guild.features if f in feat_map]
        if active:
            embed.add_field(
                name=f"{e('badge')}  Features",
                value="  ·  ".join(active),
                inline=False,
            )

        # ── Banner (large image) ──────────────────────────
        if guild.banner:
            embed.set_image(url=guild.banner.with_size(1024).url)
            embed.add_field(name=f"{e('banner')}  Server Banner", value="*displayed below*", inline=False)
        elif guild.splash:
            embed.set_image(url=guild.splash.with_size(1024).url)

        embed.set_footer(
            text=f"Requested by {ctx.author}  ·  {guild.member_count:,} members",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────
    # ,avatar
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="avatar", aliases=["av", "pfp", "icon"])
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        color  = member.color if str(member.color) != "#000000" else BLURPLE

        embed = discord.Embed(
            description=(
                f"{e('avatar')}  **{member.mention}'s Avatar**\n"
                + (f"> Has a server-specific avatar.\n" if member.guild_avatar else "")
            ),
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=f"{member}  ·  Avatar", icon_url=member.display_avatar.url)
        embed.set_image(url=member.display_avatar.replace(size=4096).url)

        base  = member.display_avatar.replace(size=4096)
        links = []
        for fmt in ("png", "jpg", "webp"):
            try: links.append(f"[{fmt.upper()}]({base.replace(format=fmt).url})")
            except Exception: pass
        if member.display_avatar.is_animated():
            try: links.append(f"[GIF]({base.replace(format='gif').url})")
            except Exception: pass

        embed.add_field(name=f"{e('link')}  Download", value="  |  ".join(links) or "N/A", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────
    # ,banner
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="banner", aliases=["userbanner", "sb"])
    async def banner(self, ctx: commands.Context, member: discord.Member = None):
        if member:
            try:
                fetched = await self.bot.fetch_user(member.id)
            except Exception:
                fetched = None

            if not fetched or not fetched.banner:
                await ctx.send(embed=discord.Embed(
                    description=f"> {e('warning')}  **{member}** has no profile banner.",
                    color=ORANGE,
                ))
                return

            color = member.color if str(member.color) != "#000000" else BLURPLE
            embed = discord.Embed(
                description=f"{e('banner')}  **{member.mention}'s Banner**",
                color=color,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_author(name=f"{member}  ·  Profile Banner", icon_url=member.display_avatar.url)
            embed.set_image(url=fetched.banner.replace(size=4096).url)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        else:
            guild = ctx.guild
            if not guild.banner:
                await ctx.send(embed=discord.Embed(
                    description=f"> {e('warning')}  This server has no banner. (Requires Level 2 boost)",
                    color=ORANGE,
                ))
                return

            embed = discord.Embed(
                description=f"{e('banner')}  **{guild.name}'s Server Banner**",
                color=BLURPLE,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_author(
                name=f"{guild.name}  ·  Server Banner",
                icon_url=guild.icon.url if guild.icon else discord.Embed.Empty,
            )
            embed.set_image(url=guild.banner.replace(size=4096).url)

            b    = guild.banner.replace(size=4096)
            refs = (
                f"[PNG]({b.replace(format='png').url})  |  "
                f"[JPG]({b.replace(format='jpg').url})  |  "
                f"[WEBP]({b.replace(format='webp').url})"
            )
            if guild.banner.is_animated():
                refs += f"  |  [GIF]({b.replace(format='gif').url})"

            embed.add_field(name=f"{e('link')}  Download", value=refs, inline=False)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))
