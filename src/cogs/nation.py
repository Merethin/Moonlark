from discord.ext import commands
import sans, asyncio, re
from .recruit import RecruitmentManager

FOUND_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ was (founded|refounded) in %%([a-z0-9_\-]+)%%")
WA_JOIN_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ was admitted to the World Assembly")

class NationListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sse_task = asyncio.create_task(self.sse_loop())
        
    async def sse_loop(self):
        recruiter: RecruitmentManager = self.bot.get_cog('RecruitmentManager')

        client = sans.AsyncClient()
        async for event in sans.serversent_events(client, "founding", "member"):
            match = FOUND_REGEX.match(event["str"])
            if match is not None:
                groups = match.groups()
                nation = groups[0]

                if groups[1] == 'founded':
                    recruiter.add_newfound(nation)
                else:
                    recruiter.add_refound(nation)

                self.bot.dispatch('new_recruit', nation)

                print(f"log: {nation} was {groups[1]} in {groups[2]}")
                continue

            match = WA_JOIN_REGEX.match(event["str"])
            if match is not None:
                groups = match.groups()
                nation = groups[0]
                recruiter.add_new_wa(nation)

                self.bot.dispatch('new_recruit', nation)

                print(f"log: {nation} joined the World Assembly")
                continue