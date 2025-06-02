from discord.ext import commands
import sans, asyncio, re
from .recruit import RecruitmentManager

FOUND_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ was (founded|refounded) in %%([a-z0-9_\-]+)%%")
WA_JOIN_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ was admitted to the World Assembly")
MOVE_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ relocated from %%([a-z0-9_\-]+)%% to %%([a-z0-9_\-]+)%%")

# Nations that move to one of these regions and then join the WA shouldn't be recruited.
JUMP_POINT_LIST = [
    "suspicious",
    "artificial_solar_system"
]

class NationListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sse_task = asyncio.create_task(self.sse_loop())
        self.military_blacklist = set() # R/D puppets. Don't recruit them when they join the WA.
        
    async def sse_loop(self):
        recruiter: RecruitmentManager = self.bot.get_cog('RecruitmentManager')

        client = sans.AsyncClient()
        async for event in sans.serversent_events(client, "founding", "member", "move"):
            match = FOUND_REGEX.match(event["str"])
            if match is not None:
                groups = match.groups()
                nation = groups[0]

                if recruiter.check_puppet_filter(nation):
                    continue

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

                if nation in self.military_blacklist:
                    continue # R/D puppet, skip
                
                if recruiter.check_puppet_filter(nation):
                    continue

                recruiter.add_new_wa(nation)

                self.bot.dispatch('new_recruit', nation)

                print(f"log: {nation} joined the World Assembly")
                continue

            match = MOVE_REGEX.match(event["str"])
            if match is not None:
                groups = match.groups()
                nation = groups[0]
                target = groups[2]

                if target in JUMP_POINT_LIST:
                    self.military_blacklist.add(nation)

                continue