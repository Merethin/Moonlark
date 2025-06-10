from discord.ext import commands
import sans, asyncio, re
from .recruit import RecruitmentManager
import utility as util

FOUND_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ was (founded|refounded) in %%([a-z0-9_\-]+)%%")
WA_JOIN_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ was admitted to the World Assembly")

# Nations that move to one of these regions and then join the WA shouldn't be recruited.
JUMP_POINT_LIST = [
    "suspicious",
    "artificial_solar_system"
]

class NationListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sse_task = asyncio.create_task(self.sse_loop())

    async def sse_loop(self):
        recruiter: RecruitmentManager = self.bot.get_cog('RecruitmentManager')

        client = sans.AsyncClient()
        while True:
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
                        skip = False
                        response = await client.get(sans.Nation(nation, 'tgcanrecruit'))
                        for item in response.iter_xml():
                            if item.tag == 'TGCANRECRUIT':
                                if int(item.text) == 0:
                                    print(f"log: skipping refounded nation {nation} as it has recruitment telegrams turned off")
                                    skip = True
                                    break

                        if skip:
                            continue

                        recruiter.add_refound(nation)

                    self.bot.dispatch('new_recruit', nation)

                    print(f"log: {nation} was {groups[1]} in {groups[2]}")
                    continue

                match = WA_JOIN_REGEX.match(event["str"])
                if match is not None:
                    groups = match.groups()
                    nation = groups[0]
                    
                    if recruiter.check_puppet_filter(nation):
                        continue

                    skip = False
                    response = await client.get(sans.Nation(nation, 'region', 'tgcanrecruit', 'population'))
                    for item in response.iter_xml():
                        if item.tag == 'TGCANRECRUIT':
                            if int(item.text) == 0:
                                print(f"log: skipping new wa nation {nation} as it has recruitment telegrams turned off")
                                skip = True
                                break
                        if item.tag == 'POPULATION':
                            if int(item.text) > 500:
                                print(f"log: skipping new wa nation {nation} as it has over 500 million population")
                                skip = True
                                break
                        if item.tag == 'REGION':
                            if util.format_nation_or_region(item.text) in JUMP_POINT_LIST:
                                print(f"log: skipping new wa nation {nation} as it is in a known jump point ({item.text})")
                                skip = True
                                break

                    if skip:
                        continue

                    recruiter.add_new_wa(nation)

                    self.bot.dispatch('new_recruit', nation)

                    print(f"log: {nation} joined the World Assembly")
                    continue
            
            print("log: SSE disconnected, attempting to reconnect")