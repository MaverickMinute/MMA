import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import pytz

from utils.logger import (
    get_log_number, save_log, get_log, update_log,
    get_user_history, get_notes, add_note,
    wipe_user_record, wipe_all_records, get_wipes,
    reset_log_count
)
import config

EASTERN = pytz.timezone("US/Eastern")

def now_et():
    return datetime.now(EASTERN)

def timestamp_str(dt):
    return dt.strftime("%B %d, %Y %I:%M %p ET")

def has_role(*role_ids):
    def predicate(interaction: discord.Interaction) -> bool:
        user_role_ids = [r.id for r in interaction.user.roles]
        return any(rid in user_role_ids for rid in role_ids)
    return app_commands.check(predicate)

MOD_AND_ABOVE   = (config.ROLE_MOD, config.ROLE_ADMIN, config.ROLE_HEAD_MOD)
ADMIN_AND_ABOVE = (config.ROLE_ADMIN, config.ROLE_HEAD_MOD)
HEAD_MOD_ONLY   = (config.ROLE_HEAD_MOD,)

GUILD_ID = 1496324891438223370

async def get_log_channel(interaction):
    log_channel = discord.utils.get(interaction.guild.text_channels, name=config.LOG_CHANNEL_NAME)
    if not log_channel:
        await interaction.response.send_message("Log channel not found.", ephemeral=True)
        return None
    return log_channel


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ───────────────────────────── /warn ─────────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(user="User to warn", type="Type of warning", reason="Reason for warning")
    @app_commands.choices(type=[
        app_commands.Choice(name="Minor", value="minor"),
        app_commands.Choice(name="Major", value="major")
    ])
    @has_role(*MOD_AND_ABOVE)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, type: app_commands.Choice[str], reason: str):
        try:
            log_channel = await get_log_channel(interaction)
            if not log_channel:
                return

            log_number = get_log_number()
            now = now_et()

            if type.value == "minor":
                color = discord.Color.yellow()
                emoji = config.EMOJI_MINOR
            else:
                color = discord.Color.from_rgb(255, 100, 0)
                emoji = config.EMOJI_MAJOR

            embed = discord.Embed(
                title=f"{emoji} Log #{log_number} — {type.name} Warning",
                color=color,
                timestamp=now
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
            embed.add_field(name="User", value=user.mention, inline=False)
            embed.add_field(name="Type", value=f"{emoji} {type.name}", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=timestamp_str(now))

            msg = await log_channel.send(embed=embed)
            save_log(log_number, msg.id, user.id, "warn", type=type.value, reason=reason)
            await interaction.response.send_message(f"{emoji} {user.mention} has been warned.", ephemeral=True)

        except Exception as e:
            print(f"Error in /warn: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /kick ─────────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="kick", description="Kick a user")
    @app_commands.describe(user="User to kick", reason="Reason for kick")
    @has_role(*ADMIN_AND_ABOVE)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        try:
            log_channel = await get_log_channel(interaction)
            if not log_channel:
                return

            log_number = get_log_number()
            now = now_et()

            embed = discord.Embed(
                title=f"👢 Log #{log_number} — Kick",
                color=discord.Color.from_rgb(255, 165, 0),
                timestamp=now
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
            embed.add_field(name="User", value=user.mention, inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=timestamp_str(now))

            msg = await log_channel.send(embed=embed)
            save_log(log_number, msg.id, user.id, "kick", reason=reason)
            await user.kick(reason=reason)
            await interaction.response.send_message(f"👢 {user.mention} has been kicked.", ephemeral=True)

        except Exception as e:
            print(f"Error in /kick: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /ban ──────────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="ban", description="Ban a user")
    @app_commands.describe(user="User to ban", reason="Reason for ban")
    @has_role(*ADMIN_AND_ABOVE)
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        try:
            log_channel = await get_log_channel(interaction)
            if not log_channel:
                return

            log_number = get_log_number()
            now = now_et()

            embed = discord.Embed(
                title=f"{config.EMOJI_BAN} Log #{log_number} — Ban",
                color=discord.Color.from_rgb(139, 0, 0),
                timestamp=now
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
            embed.add_field(name="User", value=user.mention, inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=timestamp_str(now))

            msg = await log_channel.send(embed=embed)
            save_log(log_number, msg.id, user.id, "ban", reason=reason)
            await user.ban(reason=reason)
            await interaction.response.send_message(f"{config.EMOJI_BAN} {user.mention} has been banned.", ephemeral=True)

        except Exception as e:
            print(f"Error in /ban: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /timeout ──────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(user="User to timeout", duration="Duration in minutes", reason="Reason for timeout")
    @has_role(*MOD_AND_ABOVE)
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: int, reason: str):
        try:
            log_channel = await get_log_channel(interaction)
            if not log_channel:
                return

            log_number = get_log_number()
            now = now_et()

            embed = discord.Embed(
                title=f"{config.EMOJI_TIMEOUT} Log #{log_number} — Timeout",
                color=discord.Color.from_rgb(128, 0, 128),
                timestamp=now
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
            embed.add_field(name="User", value=user.mention, inline=False)
            embed.add_field(name="Duration", value=f"{duration} minute(s)", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=timestamp_str(now))

            msg = await log_channel.send(embed=embed)
            save_log(log_number, msg.id, user.id, "timeout", reason=reason)
            await user.timeout(timedelta(minutes=duration), reason=reason)
            await interaction.response.send_message(f"{config.EMOJI_TIMEOUT} {user.mention} has been timed out for {duration} minute(s).", ephemeral=True)

        except Exception as e:
            print(f"Error in /timeout: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /untimeout ────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="untimeout", description="Remove a timeout from a user")
    @app_commands.describe(user="User to untimeout", reason="Reason for removing timeout")
    @has_role(*HEAD_MOD_ONLY)
    async def untimeout(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        try:
            log_channel = await get_log_channel(interaction)
            if not log_channel:
                return

            log_number = get_log_number()
            now = now_et()

            embed = discord.Embed(
                title=f"{config.EMOJI_UNTIMEOUT} Log #{log_number} — Untimeout",
                color=discord.Color.green(),
                timestamp=now
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
            embed.add_field(name="User", value=user.mention, inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=timestamp_str(now))

            msg = await log_channel.send(embed=embed)
            save_log(log_number, msg.id, user.id, "untimeout", reason=reason)
            await user.timeout(None)
            await interaction.response.send_message(f"{config.EMOJI_UNTIMEOUT} {user.mention}'s timeout has been removed.", ephemeral=True)

        except Exception as e:
            print(f"Error in /untimeout: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /unban ────────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for unban")
    @has_role(*HEAD_MOD_ONLY)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str):
        try:
            log_channel = await get_log_channel(interaction)
            if not log_channel:
                return

            user = await self.bot.fetch_user(int(user_id))
            log_number = get_log_number()
            now = now_et()

            embed = discord.Embed(
                title=f"✅ Log #{log_number} — Unban",
                color=discord.Color.green(),
                timestamp=now
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=timestamp_str(now))

            msg = await log_channel.send(embed=embed)
            save_log(log_number, msg.id, user.id, "unban", reason=reason)
            await interaction.guild.unban(user, reason=reason)
            await interaction.response.send_message(f"✅ {user} has been unbanned.", ephemeral=True)

        except Exception as e:
            print(f"Error in /unban: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /undo ─────────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="undo", description="Undo a moderation action by log number")
    @app_commands.describe(log_number="The log number to undo")
    @has_role(*HEAD_MOD_ONLY)
    async def undo(self, interaction: discord.Interaction, log_number: int):
        try:
            log_channel = await get_log_channel(interaction)
            if not log_channel:
                return

            log_entry = get_log(log_number)
            if not log_entry:
                await interaction.response.send_message(f"Log #{log_number} not found.", ephemeral=True)
                return

            try:
                original_msg = await log_channel.fetch_message(log_entry["message_id"])
                await original_msg.delete()
            except Exception:
                pass

            now = now_et()
            new_log_number = get_log_number()
            action = log_entry["action"]
            user_id = log_entry["user_id"]

            embed = discord.Embed(
                title=f"↩️ Log #{new_log_number} — Undo {action.capitalize()} (was Log #{log_number})",
                color=discord.Color.blurple(),
                timestamp=now
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
            embed.add_field(name="Affected User", value=f"<@{user_id}>", inline=False)
            embed.add_field(name="Original Action", value=action.capitalize(), inline=False)
            embed.add_field(name="Original Reason", value=log_entry.get("reason") or "N/A", inline=False)
            embed.set_footer(text=timestamp_str(now))

            msg = await log_channel.send(embed=embed)
            save_log(new_log_number, msg.id, user_id, f"undo_{action}")
            await interaction.response.send_message(f"↩️ Log #{log_number} has been undone.", ephemeral=True)

        except Exception as e:
            print(f"Error in /undo: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /redo ─────────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="redo", description="Edit the reason or severity of an existing log")
    @app_commands.describe(
        log_number="The log number to edit",
        new_reason="New reason (leave blank to keep original)",
        new_type="New warning type (only for warn logs)"
    )
    @app_commands.choices(new_type=[
        app_commands.Choice(name="Minor", value="minor"),
        app_commands.Choice(name="Major", value="major")
    ])
    @has_role(*HEAD_MOD_ONLY)
    async def redo(self, interaction: discord.Interaction, log_number: int, new_reason: str = None, new_type: app_commands.Choice[str] = None):
        try:
            log_channel = await get_log_channel(interaction)
            if not log_channel:
                return

            log_entry = get_log(log_number)
            if not log_entry:
                await interaction.response.send_message(f"Log #{log_number} not found.", ephemeral=True)
                return

            if not new_reason and not new_type:
                await interaction.response.send_message("You must provide a new reason and/or a new type.", ephemeral=True)
                return

            original_msg = await log_channel.fetch_message(log_entry["message_id"])
            embed = original_msg.embeds[0]
            new_embed = embed.copy()

            if new_reason:
                for i, field in enumerate(new_embed.fields):
                    if field.name == "Reason":
                        new_embed.set_field_at(i, name="Reason", value=f"{new_reason} *(edited)*", inline=False)
                update_log(log_number, reason=new_reason)

            if new_type and log_entry["action"] == "warn":
                if new_type.value == "minor":
                    new_embed.color = discord.Color.yellow()
                    emoji = config.EMOJI_MINOR
                else:
                    new_embed.color = discord.Color.from_rgb(255, 100, 0)
                    emoji = config.EMOJI_MAJOR

                for i, field in enumerate(new_embed.fields):
                    if field.name == "Type":
                        new_embed.set_field_at(i, name="Type", value=f"{emoji} {new_type.name} *(edited)*", inline=False)

                new_embed.title = f"{emoji} Log #{log_number} — {new_type.name} Warning *(edited)*"
                update_log(log_number, type=new_type.value)

            await original_msg.edit(embed=new_embed)
            await interaction.response.send_message(f"✏️ Log #{log_number} has been updated.", ephemeral=True)

        except Exception as e:
            print(f"Error in /redo: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /note ─────────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="note", description="Add a note to a user's record")
    @app_commands.describe(user="User to add a note for", note="The note to add")
    @has_role(*MOD_AND_ABOVE)
    async def note(self, interaction: discord.Interaction, user: discord.Member, note: str):
        try:
            add_note(user.id, note, interaction.user.id)
            await interaction.response.send_message(
                f"{config.EMOJI_NOTE} Note added to {user.mention}'s record.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Error in /note: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /record ───────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="record", description="View a user's full moderation record")
    @app_commands.describe(user="User to look up")
    @has_role(*MOD_AND_ABOVE)
    async def record(self, interaction: discord.Interaction, user: discord.Member):
        try:
            history = get_user_history(user.id)
            notes = get_notes(user.id)
            wipes = get_wipes(user.id)
            now = now_et()

            has_been_banned = len(history["bans"]) > 0

            user_role_ids = [r.id for r in user.roles]
            if config.ROLE_HEAD_MOD in user_role_ids:
                staff_role = "Head of Moderation"
            elif config.ROLE_ADMIN in user_role_ids:
                staff_role = "Admin"
            elif config.ROLE_MOD in user_role_ids:
                staff_role = "Moderator"
            else:
                staff_role = "None"

            joined = user.joined_at.astimezone(EASTERN).strftime("%B %d, %Y") if user.joined_at else "Unknown"

            embed = discord.Embed(
                title=f"📋 Record — {user.display_name}",
                color=discord.Color.from_rgb(30, 30, 30),
                timestamp=now
            )

            if has_been_banned:
                embed.set_thumbnail(url=config.BANNED_EMOJI_URL)

            embed.add_field(name="Username", value=str(user), inline=True)
            embed.add_field(name="Nickname", value=user.nick or "None", inline=True)
            embed.add_field(name="Joined Server", value=joined, inline=True)
            embed.add_field(name="Staff Role", value=staff_role, inline=True)
            embed.add_field(name="User ID", value=str(user.id), inline=True)

            # Warnings
            minor_warns = [w for w in history["warns"] if w.get("type") == "minor"]
            major_warns = [w for w in history["warns"] if w.get("type") == "major"]
            warn_lines = []
            for w in minor_warns:
                warn_lines.append(f"{config.EMOJI_MINOR} **Minor** — Log #{w['log_number']} — {w.get('reason', 'No reason')}")
            for w in major_warns:
                warn_lines.append(f"{config.EMOJI_MAJOR} **Major** — Log #{w['log_number']} — {w.get('reason', 'No reason')}")
            embed.add_field(
                name=f"Warnings ({len(history['warns'])})",
                value="\n".join(warn_lines) if warn_lines else "None",
                inline=False
            )

            # Bans
            ban_lines = [f"{config.EMOJI_BAN} Log #{b['log_number']} — {b.get('reason', 'No reason')}" for b in history["bans"]]
            embed.add_field(
                name=f"Bans ({len(history['bans'])})",
                value="\n".join(ban_lines) if ban_lines else "None",
                inline=False
            )

            # Kicks
            kick_lines = [f"👢 Log #{k['log_number']} — {k.get('reason', 'No reason')}" for k in history["kicks"]]
            embed.add_field(
                name=f"Kicks ({len(history['kicks'])})",
                value="\n".join(kick_lines) if kick_lines else "None",
                inline=False
            )

            # Timeouts
            timeout_lines = [f"{config.EMOJI_TIMEOUT} Log #{t['log_number']} — {t.get('reason', 'No reason')}" for t in history["timeouts"]]
            embed.add_field(
                name=f"Timeouts ({len(history['timeouts'])})",
                value="\n".join(timeout_lines) if timeout_lines else "None",
                inline=False
            )

            # Notes
            note_lines = [f"{config.EMOJI_NOTE} {n['note']} *(by <@{n['moderator_id']}>)*" for n in notes]
            embed.add_field(
                name=f"Notes ({len(notes)})",
                value="\n".join(note_lines) if note_lines else "None",
                inline=False
            )

            # Wipes
            if wipes:
                embed.add_field(
                    name=f"⚠️ Record Wiped ({len(wipes)} time{'s' if len(wipes) > 1 else ''})",
                    value="\n".join([f"By <@{w['moderator_id']}>" for w in wipes]),
                    inline=False
                )

            embed.set_footer(text=f"Maverick Auto Mod (MAM) • {timestamp_str(now)}")
            embed.set_author(name=str(user), icon_url=user.display_avatar.url)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Error in /record: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    # ───────────────────────────── /wipe ─────────────────────────────
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="wipe", description="Wipe a user's record, all records, or reset log count")
    @app_commands.describe(
        target="What to wipe",
        user="User to wipe (only for 'record')"
    )
    @app_commands.choices(target=[
        app_commands.Choice(name="Record — Wipe a single user's record", value="record"),
        app_commands.Choice(name="Records — Wipe everyone's records", value="records"),
        app_commands.Choice(name="Logs — Reset the log counter to 0", value="logs"),
    ])
    @has_role(*HEAD_MOD_ONLY)
    async def wipe(self, interaction: discord.Interaction, target: app_commands.Choice[str], user: discord.Member = None):
        try:
            # ── wipe record ──
            if target.value == "record":
                if not user:
                    await interaction.response.send_message("You must specify a user to wipe.", ephemeral=True)
                    return
                wipe_user_record(user.id, interaction.user.id)
                await interaction.response.send_message(
                    f"🧹 {user.mention}'s record has been wiped.",
                    ephemeral=True
                )

            # ── wipe records (everyone) ──
            elif target.value == "records":
                wipe_all_records(interaction.user.id)
                await interaction.response.send_message(
                    "🧹 All records have been wiped.",
                    ephemeral=True
                )

            # ── wipe logs (reset counter) ──
            elif target.value == "logs":
                reset_log_count()
                await interaction.response.send_message(
                    "🔄 Log counter has been reset. The next log will be #1.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"Error in /wipe: {e}")
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))