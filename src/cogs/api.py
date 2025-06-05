from discord.ext import commands
from discord import app_commands
from .template import UserTemplates
from .recruit import RecruitmentManager
from .guilds import GuildManager
import discord, asyncio, sans, httpx, json, typing, re
from datetime import datetime
from dataclasses import dataclass

class APITGTemplate:
    category: str # The label for this telegram template
    tgid: int # The Template ID for this telegram
    key: str # The Secret Key for this telegram

    # format: "category:tgid:key"
    @staticmethod
    def from_string(string: str):
        template = APITGTemplate()

        split = string.split(":")
        template.category = split[0]
        template.tgid = int(split[1])
        template.key = split[2]

        return template
    
    def to_string(self):
        return f"{self.category}:{self.tgid}:{self.key}"

@dataclass
class APITemplates:
    wa: list[APITGTemplate] # The list of templates for new WA members
    newfound: list[APITGTemplate] # The list of templates for newfounds
    refound: list[APITGTemplate] # The list of templates for refounds

    # format: "category1:tgid1,category2:tgid2"
    @staticmethod
    def from_strings(wa: str, newfound: str, refound: str):
        wa_list = [APITGTemplate.from_string(s) for s in wa.split(",") if s.rstrip() != '']
        newfound_list = [APITGTemplate.from_string(s) for s in newfound.split(",") if s.rstrip() != '']
        refound_list = [APITGTemplate.from_string(s) for s in refound.split(",") if s.rstrip() != '']
        return UserTemplates(wa_list, newfound_list, refound_list)
    
    def to_strings(self) -> typing.Tuple[str, str, str]:
        wa = ",".join([t.to_string() for t in self.wa])
        newfound = ",".join([t.to_string() for t in self.newfound])
        refound = ",".join([t.to_string() for t in self.refound])
        return (wa, newfound, refound)

class APIRecruiter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild = None
        self.client_key = None
        self.recruitment_task = None
        self.start = datetime.now()
        self.sent = 0
        self.templates = APITemplates([], [], [])

        self.load()

    @commands.Cog.listener()
    async def on_backlog_ready(self):
        if self.guild and self.client_key and not self.recruitment_task:
            self.recruitment_task = asyncio.create_task(self.telegram_loop())

    def load(self):
        obj = {}

        try:
            with open("api.json", "r") as api_json:
                obj = json.load(api_json)
        except Exception:
            return
        
        self.guild = obj.get("guild")
        self.client_key = obj.get("client_key")
        self.templates = APITemplates.from_strings(obj.get("wa", ""), obj.get("newfound", ""), obj.get("refound", ""))

    def sync(self):
        obj = {}
        if self.guild:
            obj["guild"] = self.guild
        if self.client_key:
            obj["client_key"] = self.client_key
        (wa, newfound, refound) = self.templates.to_strings()
        obj["wa"] = wa
        obj["newfound"] = newfound
        obj["refound"] = refound

        with open("api.json", "w+") as api_json:
            json.dump(obj, api_json)

    @app_commands.command(description="Set the guild to share the queue with the API.")
    @commands.is_owner()
    async def apiguild(self, interaction: discord.Interaction):
        self.guild = interaction.guild.id
        self.sync()

        await interaction.response.send_message("API Guild updated successfully!", ephemeral=True)

    @app_commands.command(description="Set the client key to use for the API.")
    @commands.is_owner()
    async def apiclient(self, interaction: discord.Interaction, client_key: str):
        self.client_key = client_key
        self.sync()

        await interaction.response.send_message("API Client Key updated successfully!", ephemeral=True)

    @app_commands.command(description="Start API recruitment (started automatically at bot launch if a guild and API client key are set).")
    @commands.is_owner()
    async def apistart(self, interaction: discord.Interaction):
        if self.guild is None:
            await interaction.response.send_message("API guild must be set!", ephemeral=True)
            return 
        
        if self.client_key is None:
            await interaction.response.send_message("API client key must be set!", ephemeral=True)
            return
        
        if self.recruitment_task is not None:
            await interaction.response.send_message("API recruitment is already running!", ephemeral=True)
            return 
        
        self.recruitment_task = asyncio.create_task(self.telegram_loop())

        await interaction.response.send_message("API recruitment started!", ephemeral=True)

        await self.recruitment_task

    @app_commands.command(description="Stop API recruitment.")
    @commands.is_owner()
    async def apistop(self, interaction: discord.Interaction):
        task = self.recruitment_task
        if task is None:
            await interaction.response.send_message("API recruitment is not running!", ephemeral=True)
            return 
        
        self.recruitment_task = None
        task.cancel()

        await interaction.response.send_message("API recruitment stopped!", ephemeral=True)

    @app_commands.command(description="Stop and restart API recruitment.")
    @commands.is_owner()
    async def apirestart(self, interaction: discord.Interaction):
        task = self.recruitment_task
        if task is None:
            await interaction.response.send_message("API recruitment is not running!", ephemeral=True)
            return 
        
        self.recruitment_task = None
        task.cancel()

        self.recruitment_task = asyncio.create_task(self.telegram_loop())

        await interaction.response.send_message("API recruitment restarted!", ephemeral=True)

        await self.recruitment_task

    @app_commands.command(description="Show current status for API recruitment.")
    @commands.is_owner()
    async def apistatus(self, interaction: discord.Interaction):
        task = self.recruitment_task
        if task is None:
            await interaction.response.send_message("API recruitment is not running!", ephemeral=True)
            return
        
        guild_name = self.bot.get_guild(self.guild).name
        wa_templates = len(self.templates.wa)
        newfound_templates = len(self.templates.newfound)
        refound_templates = len(self.templates.refound)

        embed = discord.Embed(title="API Recruitment Status",
                      description=f"Recruiting for Guild: {guild_name}\n"
                      f"WA Templates: {wa_templates}\n"
                      f"Newfound Templates: {newfound_templates}\n"
                      f"Refound Templates: {refound_templates}\n"
                      f"Started: <t:{int(self.start.timestamp())}:R>\n"
                      f"API Telegrams Sent: {self.sent}",
                      colour=0xf8e45c,
                      timestamp=datetime.now())
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(description="List your registered API templates.")
    @commands.is_owner()
    async def apitemplates(self, interaction: discord.Interaction):
        text = ""

        if len(self.templates.wa) > 0:
            text += "**WA Templates**\n"

            for template in self.templates.wa:
                text += f"{template.category}: __{template.tgid}__ (key: {template.key}) - [Telegram Page Link](https://www.nationstates.net/tgcategory={template.category}/page=tg/tgid={template.tgid})\n"

            text += "\n"

        if len(self.templates.newfound) > 0:
            text += "**Newfound Templates**\n"

            for template in self.templates.newfound:
                text += f"{template.category}: __{template.tgid}__ (key: {template.key}) - [Telegram Page Link](https://www.nationstates.net/tgcategory={template.category}/page=tg/tgid={template.tgid})\n"

            text += "\n"

        if len(self.templates.refound) > 0:
            text += "**Refound Templates**\n"

            for template in self.templates.refound:
                text += f"{template.category}: __{template.tgid}__ (key: {template.key}) - [Telegram Page Link](https://www.nationstates.net/tgcategory={template.category}/page=tg/tgid={template.tgid})\n"

        if text.endswith("\n"):
            text = text.rstrip()

        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(description="Add a new template to your registered API templates.")
    @commands.is_owner()
    async def apiadd(self, interaction: discord.Interaction, destination: str, category: str, tgid: str, key: str):
        template = APITGTemplate()
        template.category = category
        template.key = key
        match = re.match(r"%TEMPLATE\-([0-9]+)%", tgid)
        if match is not None:
            template.tgid = int(match.groups()[0])
        else:
            await interaction.response.send_message("Template ID is invalid!", ephemeral=True)
            return

        if destination == "wa":
            self.templates.wa.append(template)
            self.sync()
            await interaction.response.send_message("WA Template added successfully!", ephemeral=True)
            return

        if destination == "newfound":
            self.templates.newfound.append(template)
            self.sync()
            await interaction.response.send_message("Newfound Template added successfully!", ephemeral=True)
            return

        if destination == "refound":
            self.templates.refound.append(template)
            self.sync()
            await interaction.response.send_message("Refound Template added successfully!", ephemeral=True)
            return
        
        await interaction.response.send_message("Error: destination must be one of 'wa', 'newfound' or 'refound'", ephemeral=True)

    @app_commands.command(description="Set up a new generic API template for all three destinations.")
    @commands.is_owner()
    async def apisetup(self, interaction: discord.Interaction, tgid: str, key: str):
        template = APITGTemplate()
        template.category = "generic"
        template.key = key
        match = re.match(r"%TEMPLATE\-([0-9]+)%", tgid)
        if match is not None:
            template.tgid = int(match.groups()[0])
        else:
            await interaction.response.send_message("Template ID is invalid!", ephemeral=True)
            return

        self.templates.wa.append(template)
        self.templates.newfound.append(template)
        self.templates.refound.append(template)
        self.sync()

        await interaction.response.send_message("API template set up successfully!", ephemeral=True)

    @app_commands.command(description="Remove all API templates matching a specific category.")
    @commands.is_owner()
    async def apiremove(self, interaction: discord.Interaction, category: str):
        removed = 0

        for template_list in [self.templates.wa, self.templates.newfound, self.templates.refound]:
            to_remove = []
            for template in template_list:
                if template.category == category:
                    to_remove.append(template)

            for template in to_remove:
                removed += 1
                template_list.remove(template)
        
        self.sync()
        await interaction.response.send_message(f"{removed} templates removed from your API template list!", ephemeral=True)

    @app_commands.command(description="Clears your registered API templates.")
    @commands.is_owner()
    async def apiclear(self, interaction: discord.Interaction):
        self.templates = APITemplates([], [], [])
        self.sync()
        
        await interaction.response.send_message("API template list cleared!", ephemeral=True)

    RECRUITMENT_DELAY = 180

    async def telegram_loop(self):
        recruit: RecruitmentManager = self.bot.get_cog('RecruitmentManager')
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        limiter = sans.TelegramLimiter(recruitment=True)

        self.start = datetime.now()
        self.sent = 0

        do_wa = guilds.guilds[self.guild].recruit_wa
        do_newfounds = guilds.guilds[self.guild].recruit_newfounds
        do_refounds = guilds.guilds[self.guild].recruit_refounds

        if len(self.templates.wa) == 0:
            do_wa = False

        if len(self.templates.newfound) == 0:
            do_newfounds = False

        if len(self.templates.refound) == 0:
            do_refounds = False

        conditions = [do_wa, do_newfounds, do_refounds]
        pop_operations = [recruit.pop_wa_nations, recruit.pop_new_nations, recruit.pop_refound_nations]
        user_templates = [self.templates.wa, self.templates.newfound, self.templates.refound]
        categories = ["wa", "newfound", "refound"]
        indexes = [0, 0, 0]

        print("log: starting API recruitment task")

        async with sans.AsyncClient() as client:
            while True:
                order = recruit.sort_queues(self.guild)

                message_sent = False

                for i in order:
                    if conditions[i]:
                        nations = pop_operations[i](self.guild, 1)
                        if len(nations) != 0:
                            target = nations[0]

                            (index, template) = recruit.select_template(user_templates[i], indexes[i])
                            indexes[i] = index

                            try:
                                print(f"log: preparing API telegram with ID {template.tgid} (category: {categories[i]}) for target '{target}'")
                                response = await client.get(sans.Telegram(client=self.client_key, tgid=str(template.tgid), key=template.key, to=target), auth=limiter)

                                self.sent += 1

                                print(f"log: API telegram {template.tgid} sent to {target}, response: {response.content.rstrip().decode("utf-8")}")

                            except httpx.ReadTimeout:
                                print("log: response timed out, skipping this target")

                            print(f"log: delaying next telegram by {self.RECRUITMENT_DELAY} seconds")

                            await asyncio.sleep(self.RECRUITMENT_DELAY) # sans automatically limits the telegram speed, but we want to pick a nation after the delay's over, not before it

                            message_sent = True

                if message_sent:
                    continue

                print(f"log: no nations in queue, API task will block")
                await self.bot.wait_for('new_recruit')