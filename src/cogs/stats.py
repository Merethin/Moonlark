from discord.ext import commands
from discord import app_commands
from dataclasses import dataclass
from .db import Database
from .guilds import GuildManager
import discord, typing
from pagination import Pagination
from datetime import date, timedelta

@dataclass
class Stats:
    wa_sent: int
    newfound_sent: int
    refound_sent: int

# Stores statistics for telegrams sent in a guild.
class StatsTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stat_map: dict[tuple[int, int, date], Stats] = {}

        self.load()

    def load(self):
        database: Database = self.bot.get_cog('Database')
        cursor = database.db.cursor()

        cursor.execute("SELECT * FROM stats")
        data = cursor.fetchall()

        for stat_line in data:
            self.stat_map[(stat_line[1], stat_line[2], date(stat_line[3], stat_line[4], stat_line[5]))] = Stats(stat_line[6], stat_line[7], stat_line[8])

        cursor.close()

    def sync(self, guild_id: int, user_id: int, today: date):
        database: Database = self.bot.get_cog('Database')
        cursor = database.db.cursor()

        stat = self.stat_map[(guild_id, user_id, today)]

        data = (f"{guild_id}-{user_id}-{today.year}-{today.month}-{today.day}", guild_id, user_id, today.year, today.month, today.day, stat.wa_sent, stat.newfound_sent, stat.refound_sent)
        cursor.execute("INSERT OR REPLACE INTO stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", data)

        database.db.commit()
        cursor.close()

    def update_stats(self, guild_id: int, user_id: int, update_wa: int, update_newfound: int, update_refound: int):
        today = date.today()

        stat = self.stat_map.get((guild_id, user_id, today))

        if stat is None:
            self.stat_map[(guild_id, user_id, today)] = Stats(update_wa, update_newfound, update_refound)
        else:
            stat.wa_sent += update_wa
            stat.newfound_sent += update_newfound
            stat.refound_sent += update_refound
            self.stat_map[(guild_id, user_id, today)] = stat

        self.sync(guild_id, user_id, today)

    @app_commands.command(description="Show recruiter stats for this guild, optionally in a specific time range (measured in days).")
    async def stats(self, interaction: discord.Interaction, since: typing.Optional[int]):
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        if not await guilds.check_recruit_permissions(interaction):
            return
        
        start_day = None
        if since is not None:
            start_day = date.today() - timedelta(days=since)
        
        recruiter_dict = {}

        for (guild_id, user_id, day), stat in self.stat_map.items():
            if guild_id == interaction.guild.id:
                if start_day is not None:
                    if day < start_day:
                        continue

                name = ""
                member = interaction.guild.get_member(user_id)
                if member is None:
                    name = f"[@{user_id}]" # Member is no longer in the guild
                else:
                    name = f"{member.name}"

                if name not in recruiter_dict.keys():
                    recruiter_dict[name] = (stat.wa_sent+stat.newfound_sent+stat.refound_sent, stat.wa_sent, stat.newfound_sent, stat.refound_sent)
                else:
                    recruiter_dict[name][0] += stat.wa_sent+stat.newfound_sent+stat.refound_sent
                    recruiter_dict[name][1] += stat.wa_sent
                    recruiter_dict[name][2] += stat.newfound_sent
                    recruiter_dict[name][3] += stat.refound_sent

        recruiters = [(name, total, wa, newfound, refound) for (name, (total, wa, newfound, refound)) in recruiter_dict.items()]

        # Sort by total telegrams sent
        recruiters.sort(reverse=True, key=lambda a: a[1])

        if(len(recruiters) == 0):
            if start_day is None:
                await interaction.response.send_message(f"No one has sent recruitment telegrams for {interaction.guild.name}!")
            else:
                await interaction.response.send_message(f"No one has sent recruitment telegrams for {interaction.guild.name} since {start_day.day}/{start_day.month}/{start_day.year}!")
            return

        ELEMENTS_PER_PAGE = 10

        heading = ""
        if start_day is None:
            heading = "All time statistics"
        else:
            heading = f"Since {start_day.day}/{start_day.month}/{start_day.year}"

        async def get_page(page: int):
            emb = discord.Embed(title=f"Statistics for {interaction.guild.name}", description="", colour=0xc061cb)
            emb.set_author(name=heading)
            offset = (page-1) * ELEMENTS_PER_PAGE
            for recruiter in recruiters[offset:offset+ELEMENTS_PER_PAGE]:
                emb.description += f"`{recruiter[0]}` - {recruiter[1]} Total ({recruiter[2]} WA, {recruiter[3]} Newfounds, {recruiter[4]} Refounds)\n"
            n = Pagination.compute_total_pages(len(recruiters), ELEMENTS_PER_PAGE)
            emb.set_footer(text=f"Page {page} of {n}")
            return emb, n

        await Pagination(interaction, get_page).navigate()

