from discord.ext import commands
from discord import app_commands
from collections import deque
from .template import TGTemplate, TemplateManager
from .guilds import GuildManager
import typing, discord, asyncio, random
from datetime import datetime

BACKLOG_SIZE = 400
MAX_NATIONS_PER_TG = 8

class RecruiterView(discord.ui.View):
    def __init__(self, user: discord.User | discord.Member, url: str):
        super().__init__()
        button = discord.ui.Button(label='Click to Send TG', style=discord.ButtonStyle.url, url=url)
        self.add_item(button)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction[discord.Client]) -> bool:
        if interaction.user == self.user:
            return True
        await interaction.response.send_message(f"The command was initiated by {self.user.mention}", ephemeral=True)
        return False

class RecruitmentManager(commands.Cog):
    def __init__(self, bot: commands.Bot, nation: str):
        self.bot = bot
        self.recruiters: dict[tuple[int, int], typing.Awaitable[None]] = {}
        self.wa_queue: dict[int, deque] = {}
        self.newfound_queue: dict[int, deque] = {}
        self.refound_queue: dict[int, deque] = {}
        self.nation = nation

    @commands.Cog.listener()
    async def on_ready(self):
        self.update_backlog()

    def update_backlog(self):
        for guild in self.bot.guilds:
            print(f"Updating backlog queues for guild {guild.name}")
            if guild.id not in self.wa_queue.keys():
                self.wa_queue[guild.id] = deque(maxlen=BACKLOG_SIZE)
            if guild.id not in self.newfound_queue.keys():
                self.newfound_queue[guild.id] = deque(maxlen=BACKLOG_SIZE)
            if guild.id not in self.refound_queue.keys():
                self.refound_queue[guild.id] = deque(maxlen=BACKLOG_SIZE)

    def add_new_wa(self, nation: str):
        for guild, queue in self.wa_queue.items():
            queue.append(nation)

    def add_newfound(self, nation: str):
        for guild, queue in self.newfound_queue.items():
            queue.append(nation)

    def add_refound(self, nation: str):
        for guild, queue in self.refound_queue.items():
            queue.append(nation)

    def pop_wa_nations(self, guild: int, max: int) -> list[str]:
        result = []
        queue = self.wa_queue.get(guild)
        if queue is None:
            queue = deque(maxlen=BACKLOG_SIZE)
            self.wa_queue[guild] = queue

        for i in range(max):
            if queue:
                result.append(queue.pop())
            else:
                break

        return result
    
    def pop_new_nations(self, guild: int, max: int) -> list[str]:
        result = []
        queue = self.newfound_queue.get(guild)
        if queue is None:
            queue = deque(maxlen=BACKLOG_SIZE)
            self.newfound_queue[guild] = queue

        for i in range(max):
            if queue:
                result.append(queue.pop())
            else:
                break

        return result

    def pop_refound_nations(self, guild: int, max: int) -> list[str]:
        result = []
        queue = self.refound_queue.get(guild)
        if queue is None:
            queue = deque(maxlen=BACKLOG_SIZE)
            self.refound_queue[guild] = queue

        for i in range(max):
            if queue:
                result.append(queue.pop())
            else:
                break

        return result
    
    def select_template(self, templates: list[TGTemplate], index: int) -> tuple[int, TGTemplate]:
        tg = templates[index]

        index += 1
        if index >= len(templates):
            index = 0

        return (index, tg)
    
    def generate_telegram_link(self, template: TGTemplate, nations: list[str], container: str | None) -> str:
        if container is None:
            return f'https://www.nationstates.net/page=compose_telegram?tgto={",".join(nations)}&message=%TEMPLATE-{template.tgid}%&generated_by=moonlark_discord_bot__by_merethin__ran_by_{self.nation}'
        else:
            return f'https://www.nationstates.net/container={container}/page=compose_telegram?tgto={",".join(nations)}&message=%TEMPLATE-{template.tgid}%&generated_by=moonlark_discord_bot__by_merethin__ran_by_{self.nation}'
    
    async def send_recruitment_embed(self, interaction: discord.Interaction, type: str, template: TGTemplate, nations: list[str], container: str | None):
        view = RecruiterView(interaction.user, self.generate_telegram_link(template, nations, container))
        embed = discord.Embed(title="New Nations to Recruit",
                      description=f"{len(nations)} {type} nations are ready to telegram!",
                      colour=0xf8e45c,
                      timestamp=datetime.now())
        
        await interaction.channel.send(
            f"{interaction.user.mention}",
            embed=embed,
            view=view,
        )

    async def recruit_task(self, interaction: discord.Interaction, interval: int, container: str | None) -> None:
        templates: TemplateManager = self.bot.get_cog('TemplateManager')
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        user_template = templates.user_templates[(interaction.guild.id, interaction.user.id)]

        do_wa = guilds.guilds[interaction.guild.id].recruit_wa
        do_newfounds = guilds.guilds[interaction.guild.id].recruit_newfounds
        do_refounds = guilds.guilds[interaction.guild.id].recruit_refounds

        if len(user_template.wa) == 0:
            do_wa = False

        if len(user_template.newfound) == 0:
            do_newfounds = False

        if len(user_template.refound) == 0:
            do_refounds = False
        
        wa_index = 0
        newfound_index = 0
        refound_index = 0

        conditions = [do_wa, do_newfounds, do_refounds]
        pop_operations = [self.pop_wa_nations, self.pop_new_nations, self.pop_refound_nations]
        user_templates = [user_template.wa, user_template.newfound, user_template.refound]
        labels = ["New WA", "Newly Founded", "Refounded"]
        indexes = [0, 0, 0]

        await interaction.response.send_message(f"{interaction.user.mention} has started recruiting every {interval} seconds")

        while True:
            print(f"log: next recruitment message for {interaction.user.name} in {interval} seconds")
            await asyncio.sleep(interval)

            while True:
                # Randomize order
                order = random.sample(range(3), 3)

                message_sent = False

                for i in order:
                    if conditions[i]:
                        nations = pop_operations[i](interaction.guild.id, MAX_NATIONS_PER_TG)
                        if len(nations) != 0:
                            (index, template) = self.select_template(user_templates[i], indexes[i])
                            indexes[i] = index

                            await self.send_recruitment_embed(interaction, labels[i], template, nations, container)
                            message_sent = True
                            break

                if message_sent:
                    break

                print(f"log: no new nations, waiting for something to happen")
                # None of these are available? Let's wait until a new recruit is found.
                _ = await self.bot.wait_for('new_recruit')

    @app_commands.command(description="Start a recruitment session.")
    async def recruit(self, interaction: discord.Interaction, interval: int, container: str | None):
        templates: TemplateManager = self.bot.get_cog('TemplateManager')
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        if not await guilds.check_recruit_permissions(interaction):
            return

        if (interaction.guild.id, interaction.user.id) not in templates.user_templates.keys():
            await interaction.response.send_message(f"You do not have any templates set in this guild!", ephemeral=True)
            return
        
        if (interaction.guild.id, interaction.user.id) in self.recruiters.keys():
            await interaction.response.send_message(f"You are already recruiting!", ephemeral=True)
            return
        
        task = asyncio.create_task(self.recruit_task(interaction, interval, container))
        self.recruiters[(interaction.guild.id, interaction.user.id)] = task

        await task

    @app_commands.command(description="Stop a recruitment session.")
    async def stop(self, interaction: discord.Interaction):
        guilds: GuildManager = self.bot.get_cog('GuildManager')

        if not await guilds.check_recruit_permissions(interaction):
            return
        
        if (interaction.guild.id, interaction.user.id) not in self.recruiters.keys():
            await interaction.response.send_message(f"You are not recruiting!", ephemeral=True)
            return
        
        task = self.recruiters[(interaction.guild.id, interaction.user.id)]
        task.cancel()

        del self.recruiters[(interaction.guild.id, interaction.user.id)]

        await interaction.response.send_message(f"Recruitment task stopped.")