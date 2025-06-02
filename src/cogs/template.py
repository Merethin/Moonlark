from dataclasses import dataclass
from discord.ext import commands
from discord import app_commands
from .db import Database
from .guilds import GuildManager
import typing, discord, re

class TGTemplate:
    category: str # The label for this telegram template
    tgid: int # The Template ID for this telegram

    # format: "category:tgid"
    @staticmethod
    def from_string(string: str):
        template = TGTemplate()

        split = string.split(":")
        template.category = split[0]
        template.tgid = int(split[1])

        return template
    
    def to_string(self):
        return f"{self.category}:{self.tgid}"

@dataclass
class UserTemplates:
    wa: list[TGTemplate] # The list of templates for new WA members
    newfound: list[TGTemplate] # The list of templates for newfounds
    refound: list[TGTemplate] # The list of templates for refounds

    # format: "category1:tgid1,category2:tgid2"
    @staticmethod
    def from_strings(wa: str, newfound: str, refound: str):
        wa_list = [TGTemplate.from_string(s) for s in wa.split(",") if s.rstrip() != '']
        newfound_list = [TGTemplate.from_string(s) for s in newfound.split(",") if s.rstrip() != '']
        refound_list = [TGTemplate.from_string(s) for s in refound.split(",") if s.rstrip() != '']
        return UserTemplates(wa_list, newfound_list, refound_list)
    
    def to_strings(self) -> typing.Tuple[str, str, str]:
        wa = ",".join([t.to_string() for t in self.wa])
        newfound = ",".join([t.to_string() for t in self.newfound])
        refound = ",".join([t.to_string() for t in self.refound])
        return (wa, newfound, refound)
    
class TemplateManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_templates: dict[tuple[int, int], UserTemplates] = {}

        self.load()

    def load(self):
        database: Database = self.bot.get_cog('Database')
        cursor = database.db.cursor()

        cursor.execute("SELECT * FROM user_templates")
        data = cursor.fetchall()

        # Load user template data from the database
        for template_group in data:
            self.user_templates[(template_group[1], template_group[2])] = UserTemplates.from_strings(template_group[3], template_group[4], template_group[5])

        cursor.close()

    def sync(self, interaction: discord.Interaction, templates: UserTemplates):
        database: Database = self.bot.get_cog('Database')
        cursor = database.db.cursor()

        (wa, newfounds, refounds) = templates.to_strings()
        data = (f"{interaction.guild.id}-{interaction.user.id}", interaction.guild.id, interaction.user.id, wa, newfounds, refounds)
        cursor.execute("INSERT OR REPLACE INTO user_templates VALUES (?, ?, ?, ?, ?, ?)", data)
        database.db.commit()
        cursor.close()

    @app_commands.command(description="List your registered templates.")
    async def templates(self, interaction: discord.Interaction):
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        if not await guilds.check_recruit_permissions(interaction):
            return

        if (interaction.guild.id, interaction.user.id) not in self.user_templates.keys():
            await interaction.response.send_message(f"You do not have any templates set in this guild!", ephemeral=True)
            return
        
        templates = self.user_templates[(interaction.guild.id, interaction.user.id)]

        text = ""

        if len(templates.wa) > 0:
            text += "**WA Templates**\n"

            for template in templates.wa:
                text += f"{template.category}: __{template.tgid}__ - [Telegram Page Link](https://www.nationstates.net/tgcategory={template.category}/page=tg/tgid={template.tgid})\n"

            text += "\n"

        if len(templates.newfound) > 0:
            text += "**Newfound Templates**\n"

            for template in templates.newfound:
                text += f"{template.category}: __{template.tgid}__ - [Telegram Page Link](https://www.nationstates.net/tgcategory={template.category}/page=tg/tgid={template.tgid})\n"

            text += "\n"

        if len(templates.refound) > 0:
            text += "**Refound Templates**\n"

            for template in templates.refound:
                text += f"{template.category}: __{template.tgid}__ - [Telegram Page Link](https://www.nationstates.net/tgcategory={template.category}/page=tg/tgid={template.tgid})\n"

        if text.endswith("\n"):
            text = text.rstrip()

        await interaction.response.send_message(text)

    @app_commands.command(description="Add a new template to your registered templates.")
    async def add(self, interaction: discord.Interaction, destination: str, category: str, tgid: str):
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        if not await guilds.check_recruit_permissions(interaction):
            return

        if (interaction.guild.id, interaction.user.id) not in self.user_templates.keys():
            self.user_templates[(interaction.guild.id, interaction.user.id)] = UserTemplates([], [], [])
        
        templates = self.user_templates[(interaction.guild.id, interaction.user.id)]

        template = TGTemplate()
        template.category = category
        match = re.match(r"%TEMPLATE\-([0-9]+)%", tgid)
        if match is not None:
            template.tgid = int(match.groups()[0])
        else:
            await interaction.response.send_message("Template ID is invalid!", ephemeral=True)
            return

        if destination == "wa":
            templates.wa.append(template)
            self.sync(interaction, templates)
            await interaction.response.send_message("WA Template added successfully!")
            return

        if destination == "newfound":
            templates.newfound.append(template)
            self.sync(interaction, templates)
            await interaction.response.send_message("Newfound Template added successfully!")
            return

        if destination == "refound":
            templates.refound.append(template)
            self.sync(interaction, templates)
            await interaction.response.send_message("Refound Template added successfully!")
            return
        
        await interaction.response.send_message("Error: destination must be one of 'wa', 'newfound' or 'refound'", ephemeral=True)

    @app_commands.command(description="Set up a new generic template for all three destinations.")
    async def setup(self, interaction: discord.Interaction, tgid: str):
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        if not await guilds.check_recruit_permissions(interaction):
            return

        if (interaction.guild.id, interaction.user.id) not in self.user_templates.keys():
            self.user_templates[(interaction.guild.id, interaction.user.id)] = UserTemplates([], [], [])
        
        templates = self.user_templates[(interaction.guild.id, interaction.user.id)]

        template = TGTemplate()
        template.category = "generic"
        match = re.match(r"%TEMPLATE\-([0-9]+)%", tgid)
        if match is not None:
            template.tgid = int(match.groups()[0])
        else:
            await interaction.response.send_message("Template ID is invalid!", ephemeral=True)
            return

        templates.wa.append(template)
        templates.newfound.append(template)
        templates.refound.append(template)
        self.sync(interaction, templates)
        await interaction.response.send_message("Template set up successfully!")

    @app_commands.command(description="Remove all templates matching a specific category.")
    async def remove(self, interaction: discord.Interaction, category: str):
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        if not await guilds.check_recruit_permissions(interaction):
            return

        if (interaction.guild.id, interaction.user.id) not in self.user_templates.keys():
            await interaction.response.send_message(f"You do not have any templates set in this guild!", ephemeral=True)
            return
        
        templates = self.user_templates[(interaction.guild.id, interaction.user.id)]

        removed = 0

        for template_list in [templates.wa, templates.newfound, templates.refound]:
            to_remove = []
            for template in template_list:
                if template.category == category:
                    to_remove.append(template)

            for template in to_remove:
                removed += 1
                template_list.remove(template)
        
        self.sync(interaction, templates)
        await interaction.response.send_message(f"{removed} templates removed from your template list!")

    @app_commands.command(description="Clears your registered templates.")
    async def clear(self, interaction: discord.Interaction):
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        if not await guilds.check_recruit_permissions(interaction):
            return

        if (interaction.guild.id, interaction.user.id) not in self.user_templates.keys():
            await interaction.response.send_message(f"You do not have any templates set in this guild!", ephemeral=True)
            return
        
        del self.user_templates[(interaction.guild.id, interaction.user.id)]

        database: Database = self.bot.get_cog('Database')
        cursor = database.db.cursor()

        cursor.execute("DELETE FROM user_templates WHERE guild_id = ? AND user_id = ?", [interaction.guild.id, interaction.user.id])
        database.db.commit()
        cursor.close()
        
        await interaction.response.send_message("Template list cleared!")