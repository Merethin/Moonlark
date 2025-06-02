from discord.ext import commands
from discord import app_commands
from dataclasses import dataclass
from .db import Database
import discord

# Stores settings for a guild.
@dataclass
class Guild:
    admin_role: int # Role that can administrate the bot.
    recruit_role: int # Role that can run recruitment.
    recruit_wa: bool # Whether to recruit new WA joins
    recruit_newfounds: bool # Whether to recruit newly founded nations
    recruit_refounds: bool # Whether to recruit refounded nations

class GuildManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guilds: dict[int, Guild] = {}

        self.load()

    def load(self):
        database: Database = self.bot.get_cog('Database')
        cursor = database.db.cursor()

        cursor.execute("SELECT * FROM guilds")
        data = cursor.fetchall()

        for guild in data:
            self.guilds[guild[0]] = Guild(guild[1], guild[2], guild[3], guild[4], guild[5])

        cursor.close()

    def sync(self, guild_id: int, guild: Guild):
        database: Database = self.bot.get_cog('Database')
        cursor = database.db.cursor()

        data = (guild_id, guild.admin_role, guild.recruit_role, guild.recruit_wa, guild.recruit_newfounds, guild.recruit_refounds)
        cursor.execute("INSERT OR REPLACE INTO guilds VALUES (?, ?, ?, ?, ?, ?)", data)
        database.db.commit()
        cursor.close()

    # Check if a command follows the following requirements:
    # 1. The guild it was run in has been configured.
    # 2. The author of the command has the Recruiter Role for that guild.
    async def check_recruit_permissions(self, interaction: discord.Interaction) -> bool:
        if interaction.guild.id not in self.guilds.keys():
            await interaction.response.send_message("This server is not configured. Tell the owner to run /config first.", ephemeral=True)
            return False

        if interaction.user.get_role(self.guilds[interaction.guild.id].recruit_role) is None:
            await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
            return False

        return True

    # Check if a command follows the following requirements:
    # 1. The guild it was run in has been configured.
    # 2. The author of the command has the Administrator Role for that guild.
    async def check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        if interaction.guild.id not in self.guilds.keys():
            await interaction.response.send_message("This server is not configured. Tell the owner to run /config first.", ephemeral=True)
            return False

        if interaction.user.get_role(self.guilds[interaction.guild.id].admin_role) is None:
            await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
            return False

        return True
    
    @app_commands.command(description="Configure the bot.")
    async def config(self, interaction: discord.Interaction, admin_role: discord.Role, recruit_role: discord.Role, recruit_wa: bool, recruit_newfounds: bool, recruit_refounds: bool):
        if interaction.user.id != interaction.guild.owner.id:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return
        
        guild = Guild(admin_role.id, recruit_role.id, recruit_wa, recruit_newfounds, recruit_refounds)
        self.sync(interaction.guild.id, guild)
        self.guilds[interaction.guild.id] = guild

        self.bot.get_cog('RecruitmentManager').update_backlog()

        await interaction.response.send_message("Server configuration updated!", ephemeral=True)