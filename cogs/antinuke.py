"""
╔══════════════════════════════════════════════════╗
║     ANTINUKE COG — Ultra-Fast Server Protection  ║
╚══════════════════════════════════════════════════╝

Speed strategy:
  • on_audit_log_entry_create  → fires the INSTANT Discord logs any action
    (no polling, no delay waiting for audit logs)
  • asyncio.create_task()      → punishment fires first, logging runs after
  • Punished-user cache        → never processes the same threat twice
  • Webhook bypass             → deletes webhook + message before it renders
  • asyncio.gather()           → parallel API calls wherever possible

Realistic minimum response time: ~50–150ms (Discord WebSocket delivery)
"""

import discord
from discord.ext import commands
import asyncio
import time
import logging
import sys
import os
from collections import defaultdict
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from icons import e

log = logging.getLogger("AntiNuke")

# ── Colour constants ──────────────────────────────────────────────────────────
RED    = discord.Color.red()
ORANGE = discord.Color.orange()
YELLOW = discord.Color.yellow()
GREEN  = discord.Color.green()
BLURPLE = 0x5865F2


def make_embed(title: str, description: str, color) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"{e('shield')}  AntiNuke Protection")
    return embed


class AntiNuke(commands.Cog):
    """🛡️ Ultra-fast anti-nuke protection system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg      = bot.config.get("antinuke", {})
        self.spam_cfg = bot.config.get("antispam", {})

        # ── Action counters: guild_id → user_id → [timestamps] ──────────
        self._ban_log:      dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._kick_log:     dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._chan_del_log: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._role_del_log: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._webhook_log:  dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._chan_cre_log: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._role_cre_log: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

        # ── Anti-spam counters ────────────────────────────────────────────
        self._msg_log:  dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._muted:    dict[int, set[int]]               = defaultdict(set)

        # ── Punishment dedup cache ────────────────────────────────────────
        # Stores guild_id → set of user_ids currently being punished
        # Prevents double-punishing the same person in a burst
        self._punishing: dict[int, set[int]] = defaultdict(set)

        # ── Whitelisted webhook IDs (populated at runtime) ────────────────
        self._wl_webhooks: dict[int, set[int]] = defaultdict(set)  # guild → webhook ids

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def is_enabled(self)      -> bool: return self.cfg.get("enabled", True)
    def is_spam_enabled(self) -> bool: return self.spam_cfg.get("enabled", True)

    def is_whitelisted(self, guild_id: int, user_id: int) -> bool:
        wl = (
            self.cfg.get("whitelisted_users", [])
            + self.cfg.get("whitelisted_bots", [])
            + self.bot.config.get("owner_ids", [])
        )
        return user_id in wl

    def _record(
        self,
        store: dict[int, dict[int, list[float]]],
        guild_id: int,
        user_id: int,
        window: float,
    ) -> int:
        now = time.monotonic()
        store[guild_id][user_id] = [t for t in store[guild_id][user_id] if now - t < window]
        store[guild_id][user_id].append(now)
        return len(store[guild_id][user_id])

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed):
        """Send to log channel — runs as a background task, never blocks punishment."""
        for name in ("antinuke-log", "mod-log", "logs", "audit-log"):
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                try:
                    await ch.send(embed=embed)
                except Exception:
                    pass
                return

    async def _punish(self, guild: discord.Guild, user_id: int, reason: str):
        """
        Apply punishment as fast as possible.
        Uses dedup cache so a burst of events only triggers one punishment.
        """
        if user_id in self._punishing[guild.id]:
            return  # Already being handled — skip
        self._punishing[guild.id].add(user_id)

        punishment = self.cfg.get("punishment", "ban")
        try:
            if punishment == "ban":
                await guild.ban(
                    discord.Object(id=user_id),
                    reason=f"[AntiNuke] {reason}",
                    delete_message_days=0,
                )
            elif punishment == "kick":
                member = guild.get_member(user_id)
                if member:
                    await member.kick(reason=f"[AntiNuke] {reason}")
            elif punishment == "strip":
                member = guild.get_member(user_id)
                if member:
                    mutable = [r for r in member.roles if r.is_assignable()]
                    if mutable:
                        await member.remove_roles(*mutable, reason=f"[AntiNuke] {reason}")
        except discord.Forbidden:
            log.warning(f"No permission to {punishment} user {user_id} in {guild.name}")
        except discord.HTTPException as ex:
            log.error(f"HTTP error punishing {user_id}: {ex}")
        finally:
            # Clear dedup after a short cooldown so re-offending is caught
            await asyncio.sleep(5)
            self._punishing[guild.id].discard(user_id)

    def _fire_punishment(self, guild: discord.Guild, user_id: int, reason: str, embed: discord.Embed):
        """
        Schedule punishment + log as non-blocking tasks.
        Punishment is ALWAYS queued first, log second.
        """
        asyncio.create_task(self._punish(guild, user_id, reason))
        asyncio.create_task(self._send_log(guild, embed))

    # ──────────────────────────────────────────────────────────────────────
    # ━━━  CORE: on_audit_log_entry_create  ━━━
    # This event fires the INSTANT Discord processes an audit log entry —
    # the fastest possible hook for detecting destructive actions.
    # ──────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        if not self.is_enabled():
            return

        guild    = entry.guild
        user     = entry.user
        if user is None:
            return
        user_id  = user.id
        action   = entry.action
        window   = self.cfg.get("time_window", 10)
        thr      = self.cfg.get("thresholds", {})
        punishment = self.cfg.get("punishment", "ban").upper()

        if self.is_whitelisted(guild.id, user_id):
            return
        if user_id == self.bot.user.id:
            return

        # ── Mass Ban ──────────────────────────────────────────────────────
        if action == discord.AuditLogAction.ban:
            count = self._record(self._ban_log, guild.id, user_id, window)
            if count >= thr.get("ban", 3):
                embed = make_embed(
                    f"{e('error')}  Mass Ban Detected",
                    (
                        f"**Offender:** <@{user_id}> (`{user_id}`)\n"
                        f"**Bans in {window}s:** `{count}`\n"
                        f"**Action:** `{punishment}`"
                    ),
                    RED,
                )
                self._fire_punishment(guild, user_id, f"Mass ban — {count} in {window}s", embed)
                self._ban_log[guild.id][user_id].clear()

        # ── Mass Kick ─────────────────────────────────────────────────────
        elif action == discord.AuditLogAction.kick:
            count = self._record(self._kick_log, guild.id, user_id, window)
            if count >= thr.get("kick", 5):
                embed = make_embed(
                    f"{e('error')}  Mass Kick Detected",
                    (
                        f"**Offender:** <@{user_id}> (`{user_id}`)\n"
                        f"**Kicks in {window}s:** `{count}`\n"
                        f"**Action:** `{punishment}`"
                    ),
                    RED,
                )
                self._fire_punishment(guild, user_id, f"Mass kick — {count} in {window}s", embed)
                self._kick_log[guild.id][user_id].clear()

        # ── Mass Channel Delete ───────────────────────────────────────────
        elif action == discord.AuditLogAction.channel_delete:
            count = self._record(self._chan_del_log, guild.id, user_id, window)
            if count >= thr.get("channel_delete", 2):
                embed = make_embed(
                    f"{e('error')}  Mass Channel Deletion",
                    (
                        f"**Offender:** <@{user_id}> (`{user_id}`)\n"
                        f"**Channels deleted in {window}s:** `{count}`\n"
                        f"**Action:** `{punishment}`"
                    ),
                    RED,
                )
                self._fire_punishment(guild, user_id, f"Mass channel delete — {count} in {window}s", embed)
                self._chan_del_log[guild.id][user_id].clear()

        # ── Mass Channel Create (spam channels) ───────────────────────────
        elif action == discord.AuditLogAction.channel_create:
            count = self._record(self._chan_cre_log, guild.id, user_id, window)
            if count >= thr.get("channel_create", 3):
                embed = make_embed(
                    f"{e('error')}  Mass Channel Creation",
                    (
                        f"**Offender:** <@{user_id}> (`{user_id}`)\n"
                        f"**Channels created in {window}s:** `{count}`\n"
                        f"**Action:** `{punishment}`"
                    ),
                    RED,
                )
                self._fire_punishment(guild, user_id, f"Mass channel create — {count} in {window}s", embed)
                self._chan_cre_log[guild.id][user_id].clear()

        # ── Mass Role Delete ──────────────────────────────────────────────
        elif action == discord.AuditLogAction.role_delete:
            count = self._record(self._role_del_log, guild.id, user_id, window)
            if count >= thr.get("role_delete", 2):
                embed = make_embed(
                    f"{e('error')}  Mass Role Deletion",
                    (
                        f"**Offender:** <@{user_id}> (`{user_id}`)\n"
                        f"**Roles deleted in {window}s:** `{count}`\n"
                        f"**Action:** `{punishment}`"
                    ),
                    RED,
                )
                self._fire_punishment(guild, user_id, f"Mass role delete — {count} in {window}s", embed)
                self._role_del_log[guild.id][user_id].clear()

        # ── Mass Role Create (spam roles) ─────────────────────────────────
        elif action == discord.AuditLogAction.role_create:
            count = self._record(self._role_cre_log, guild.id, user_id, window)
            if count >= thr.get("role_create", 3):
                embed = make_embed(
                    f"{e('error')}  Mass Role Creation",
                    (
                        f"**Offender:** <@{user_id}> (`{user_id}`)\n"
                        f"**Roles created in {window}s:** `{count}`\n"
                        f"**Action:** `{punishment}`"
                    ),
                    RED,
                )
                self._fire_punishment(guild, user_id, f"Mass role create — {count} in {window}s", embed)
                self._role_cre_log[guild.id][user_id].clear()

        # ── Mass Webhook Create ───────────────────────────────────────────
        elif action == discord.AuditLogAction.webhook_create:
            count = self._record(self._webhook_log, guild.id, user_id, window)
            if count >= thr.get("webhook_create", 3):
                embed = make_embed(
                    f"{e('error')}  Mass Webhook Creation",
                    (
                        f"**Offender:** <@{user_id}> (`{user_id}`)\n"
                        f"**Webhooks created in {window}s:** `{count}`\n"
                        f"**Action:** `{punishment}`"
                    ),
                    RED,
                )
                self._fire_punishment(guild, user_id, f"Mass webhook create — {count} in {window}s", embed)
                self._webhook_log[guild.id][user_id].clear()

        # ── Dangerous Permission Grant (admin / dangerous perms) ──────────
        elif action in (
            discord.AuditLogAction.member_role_update,
            discord.AuditLogAction.role_update,
        ):
            DANGEROUS = (
                discord.Permissions.administrator.flag
                | discord.Permissions.ban_members.flag
                | discord.Permissions.kick_members.flag
                | discord.Permissions.manage_guild.flag
                | discord.Permissions.manage_channels.flag
                | discord.Permissions.manage_roles.flag
                | discord.Permissions.manage_webhooks.flag
            )
            try:
                after = entry.after
                # Check if dangerous permissions were added
                if hasattr(after, "permissions"):
                    perms: discord.Permissions = after.permissions
                    if perms.value & DANGEROUS and not self.is_whitelisted(guild.id, user_id):
                        embed = make_embed(
                            f"{e('warning')}  Dangerous Permission Grant",
                            (
                                f"**Offender:** <@{user_id}> (`{user_id}`)\n"
                                f"**Action:** Granted dangerous permissions\n"
                                f"**Punishment:** `{punishment}`"
                            ),
                            ORANGE,
                        )
                        self._fire_punishment(guild, user_id, "Granted dangerous permissions", embed)
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────
    # Webhook Bypass Protection
    # Any message from a non-whitelisted webhook is deleted immediately
    # and the webhook itself is destroyed.
    # ──────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        # ── Webhook bypass block ──────────────────────────────────────────
        if message.webhook_id:
            guild = message.guild
            wl_webhooks = self._wl_webhooks[guild.id]

            if message.webhook_id not in wl_webhooks:
                # Unknown / non-whitelisted webhook — nuke it immediately
                async def _kill_webhook():
                    # 1. Delete the message first (fastest visual impact)
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    # 2. Fetch and delete the webhook itself
                    try:
                        webhook = await self.bot.fetch_webhook(message.webhook_id)
                        await webhook.delete(reason="[AntiNuke] Unauthorized webhook removed")
                    except Exception:
                        pass
                    # 3. Log
                    embed = make_embed(
                        f"{e('error')}  Webhook Bypass Blocked",
                        (
                            f"**Webhook ID:** `{message.webhook_id}`\n"
                            f"**Channel:** {message.channel.mention}\n"
                            f"**Action:** Message deleted · Webhook destroyed\n\n"
                            f"To whitelist a webhook, use `,antinuke wh add <webhook_id>`"
                        ),
                        ORANGE,
                    )
                    await self._send_log(guild, embed)

                asyncio.create_task(_kill_webhook())
                return  # Stop processing this message entirely

        # ── Anti-spam (human messages only) ──────────────────────────────
        if not self.is_spam_enabled():
            return
        if message.author.bot:
            return
        if self.is_whitelisted(message.guild.id, message.author.id):
            return

        guild  = message.guild
        author = message.author
        window = self.spam_cfg.get("time_window", 5)
        limit  = self.spam_cfg.get("message_limit", 7)
        count  = self._record(self._msg_log, guild.id, author.id, window)

        if count >= limit:
            if author.id in self._muted[guild.id]:
                return
            self._muted[guild.id].add(author.id)
            punishment = self.spam_cfg.get("punishment", "mute")
            mute_mins  = self.spam_cfg.get("mute_duration", 10)

            async def _spam_punish():
                try:
                    if punishment == "mute":
                        until = discord.utils.utcnow() + discord.timedelta(minutes=mute_mins)
                        await author.timeout(until, reason="[AntiSpam] Message flooding")
                    elif punishment == "kick":
                        await author.kick(reason="[AntiSpam] Message flooding")
                    elif punishment == "ban":
                        await guild.ban(author, reason="[AntiSpam] Message flooding", delete_message_days=1)
                except Exception:
                    pass

                embed = make_embed(
                    f"{e('warning')}  Anti-Spam Triggered",
                    (
                        f"**User:** {author.mention} (`{author.id}`)\n"
                        f"**Messages in {window}s:** `{count}`\n"
                        f"**Action:** `{punishment.upper()}` for `{mute_mins} min`"
                    ),
                    YELLOW,
                )
                await self._send_log(guild, embed)

                if punishment == "mute":
                    await asyncio.sleep(mute_mins * 60)
                    self._muted[guild.id].discard(author.id)

            asyncio.create_task(_spam_punish())

    # ──────────────────────────────────────────────────────────────────────
    # Unauthorized Bot Detection
    # ──────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.is_enabled() or not member.bot:
            return

        wl_bots   = self.cfg.get("whitelisted_bots", [])
        owner_ids = self.bot.config.get("owner_ids", [])

        if member.id in wl_bots or member.id in owner_ids:
            return

        async def _remove_bot():
            try:
                await member.kick(reason="[AntiNuke] Unauthorized external bot/app removed.")
            except Exception:
                pass
            embed = make_embed(
                f"{e('bot')}  Unauthorized Bot Removed",
                (
                    f"**Bot:** {member} (`{member.id}`)\n"
                    f"**Action:** Kicked (not whitelisted)\n\n"
                    f"Use `,antinuke wl add @bot` to allow it."
                ),
                ORANGE,
            )
            await self._send_log(member.guild, embed)

        asyncio.create_task(_remove_bot())

    # ──────────────────────────────────────────────────────────────────────
    # Management Commands
    # ──────────────────────────────────────────────────────────────────────

    @commands.group(name="antinuke", aliases=["an"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antinuke_group(self, ctx: commands.Context):
        """AntiNuke control panel."""
        thr = self.cfg.get("thresholds", {})
        st  = e("dot_green") + " Enabled" if self.is_enabled() else e("dot_red") + " Disabled"

        embed = discord.Embed(
            title=f"{e('shield')}  AntiNuke  ·  Control Panel",
            color=BLURPLE,
            description=(
                f"> **Status:** {st}\n"
                f"> **Punishment:** `{self.cfg.get('punishment', 'ban').upper()}`\n"
                f"> **Time Window:** `{self.cfg.get('time_window', 10)}s`"
            ),
        )
        embed.add_field(
            name=f"{e('warning')}  Thresholds",
            value=(
                f"Ban `{thr.get('ban',3)}`  ·  "
                f"Kick `{thr.get('kick',5)}`  ·  "
                f"Chan Del `{thr.get('channel_delete',2)}`  ·  "
                f"Chan Cre `{thr.get('channel_create',3)}`  ·  "
                f"Role Del `{thr.get('role_delete',2)}`  ·  "
                f"Role Cre `{thr.get('role_create',3)}`  ·  "
                f"Webhook `{thr.get('webhook_create',3)}`"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"{e('globe')}  Subcommands",
            value=(
                "`whitelist add/remove/list`  ·  "
                "`punishment <ban|kick|strip>`  ·  "
                "`toggle`  ·  "
                "`wh add/remove <id>` (webhook whitelist)"
            ),
            inline=False,
        )
        embed.set_footer(
            text=f"{e('shield')}  AntiNuke  ·  antinukebot by kold",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else discord.Embed.Empty,
        )
        await ctx.send(embed=embed)

    @antinuke_group.command(name="toggle")
    @commands.has_permissions(administrator=True)
    async def antinuke_toggle(self, ctx: commands.Context):
        self.cfg["enabled"] = not self.cfg.get("enabled", True)
        icon  = e("dot_green") if self.cfg["enabled"] else e("dot_red")
        state = "Enabled" if self.cfg["enabled"] else "Disabled"
        await ctx.send(embed=make_embed(
            f"{e('shield')}  AntiNuke Toggle",
            f"AntiNuke is now **{icon} {state}**.",
            discord.Color.blurple(),
        ))

    # ── User / Bot Whitelist ──────────────────────────────────────────────

    @antinuke_group.group(name="whitelist", aliases=["wl"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def whitelist_group(self, ctx: commands.Context):
        users = self.cfg.get("whitelisted_users", [])
        bots  = self.cfg.get("whitelisted_bots",  [])
        desc  = (
            f"{e('members')}  **Users:** {', '.join(f'<@{u}>' for u in users) or '`None`'}\n"
            f"{e('bot')}  **Bots:** {', '.join(f'<@{b}>' for b in bots) or '`None`'}"
        )
        await ctx.send(embed=make_embed(f"{e('shield')}  Whitelist", desc, discord.Color.green()))

    @whitelist_group.command(name="add")
    @commands.has_permissions(administrator=True)
    async def wl_add(self, ctx: commands.Context, member: discord.Member):
        key = "whitelisted_bots" if member.bot else "whitelisted_users"
        if member.id not in self.cfg.setdefault(key, []):
            self.cfg[key].append(member.id)
        label = "bot" if member.bot else "user"
        await ctx.send(embed=make_embed(
            f"{e('success')}  Whitelisted",
            f"{member.mention} ({label}) added to whitelist.",
            discord.Color.green(),
        ))

    @whitelist_group.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def wl_remove(self, ctx: commands.Context, member: discord.Member):
        key = "whitelisted_bots" if member.bot else "whitelisted_users"
        self.cfg[key] = [i for i in self.cfg.get(key, []) if i != member.id]
        await ctx.send(embed=make_embed(
            f"{e('error')}  Removed",
            f"{member.mention} removed from whitelist.",
            discord.Color.orange(),
        ))

    # ── Webhook Whitelist ─────────────────────────────────────────────────

    @antinuke_group.group(name="wh", aliases=["webhook"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def wh_group(self, ctx: commands.Context):
        wl = self._wl_webhooks[ctx.guild.id]
        desc = (
            f"{e('link')}  **Whitelisted Webhooks:**\n"
            + ("\n".join(f"• `{wid}`" for wid in wl) if wl else "`None`")
        )
        await ctx.send(embed=make_embed(f"{e('shield')}  Webhook Whitelist", desc, discord.Color.green()))

    @wh_group.command(name="add")
    @commands.has_permissions(administrator=True)
    async def wh_add(self, ctx: commands.Context, webhook_id: int):
        """Whitelist a webhook ID so it won't be removed."""
        self._wl_webhooks[ctx.guild.id].add(webhook_id)
        await ctx.send(embed=make_embed(
            f"{e('success')}  Webhook Whitelisted",
            f"Webhook `{webhook_id}` is now allowed.",
            discord.Color.green(),
        ))

    @wh_group.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def wh_remove(self, ctx: commands.Context, webhook_id: int):
        """Remove a webhook from the whitelist."""
        self._wl_webhooks[ctx.guild.id].discard(webhook_id)
        await ctx.send(embed=make_embed(
            f"{e('error')}  Webhook Removed",
            f"Webhook `{webhook_id}` is no longer whitelisted.",
            discord.Color.orange(),
        ))

    # ── Punishment ────────────────────────────────────────────────────────

    @antinuke_group.command(name="punishment")
    @commands.has_permissions(administrator=True)
    async def set_punishment(self, ctx: commands.Context, punishment: str):
        punishment = punishment.lower()
        if punishment not in ("ban", "kick", "strip"):
            await ctx.send(embed=make_embed(
                f"{e('error')}  Invalid Option",
                "Choose: `ban`, `kick`, or `strip`.",
                discord.Color.red(),
            ))
            return
        self.cfg["punishment"] = punishment
        await ctx.send(embed=make_embed(
            f"{e('success')}  Updated",
            f"Punishment set to `{punishment.upper()}`.",
            discord.Color.green(),
        ))


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiNuke(bot))
