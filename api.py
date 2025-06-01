import sans, asyncio, re, random, argparse, sys, json, httpx
from collections import deque
from dataclasses import dataclass
import utility as util

VERSION = "0.1.0"

@dataclass
class TGTemplate:
    tgid: int
    key: str

@dataclass
class Config:
    client: str
    templates: dict[str, list[TGTemplate]]

nation_queue = deque(maxlen=8)
filter_queue = deque(maxlen=40)
config = Config("", {})

FOUND_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ was (founded|refounded) in %%([a-z0-9_\-]+)%%")
WA_JOIN_REGEX = re.compile(r"@@([a-z0-9_\-]+)@@ was admitted to the World Assembly")

def check_puppet_filter(nation: str) -> bool:
    puppet_likeliness = 0
    for other_nation in filter_queue:
        i = 0
        for (a, b) in zip(nation,other_nation):
            if a != b:
                break
            else:
                i += 1
        if i/len(nation) > puppet_likeliness:
            puppet_likeliness = i/len(nation)

    if puppet_likeliness < 0.6:
        filter_queue.append(nation)
        return False
    else:
        print("Skipping likely puppet: {} is {} similar to existing nation".format(nation,puppet_likeliness))
        return True

async def sse_loop(asyncio_event: asyncio.Event):
    client = sans.AsyncClient()

    async for event in sans.serversent_events(client, "founding", "member"):
        match = FOUND_REGEX.match(event["str"])
        if match is not None:
            groups = match.groups()
            nation = groups[0]

            if check_puppet_filter(nation):
                continue

            if groups[1] == 'founded':
                nation_queue.append(('newfound', nation))
            else:
                nation_queue.append(('refound', nation))

            asyncio_event.set()

            print(f"log: {nation} was {groups[1]} in {groups[2]}")
            continue

        match = WA_JOIN_REGEX.match(event["str"])
        if match is not None:
            groups = match.groups()
            nation = groups[0]

            if check_puppet_filter(nation):
                continue

            nation_queue.append(('wa', nation))

            asyncio_event.set()

            print(f"log: {nation} joined the World Assembly")
            continue

RECRUITMENT_DELAY = 180

async def telegram_loop(event: asyncio.Event):
    limiter = sans.TelegramLimiter(recruitment=True)
    timeout = httpx.Timeout(10.0, read=None)

    async with sans.AsyncClient() as client:
        while True:
            if nation_queue:
                (category, nation) = nation_queue.pop()

                if category not in config.templates.keys():
                    continue

                template = random.choice(config.templates[category])

                print(f"log: preparing telegram with ID {template.tgid} (category: {category}) for target '{nation}'")
                response = await client.get(sans.Telegram(client=config.client, tgid=str(template.tgid), key=template.key, to=nation), auth=limiter, timeout=timeout)

                print(f"log: telegram {template.tgid} sent to {nation}, response: {response.content.rstrip().decode("utf-8")}")

                print(f"log: delaying next telegram by {RECRUITMENT_DELAY} seconds")

                await asyncio.sleep(RECRUITMENT_DELAY) # sans automatically limits the telegram speed, but we want to pick a nation after the delay's over, not before it
            else:
                print(f"log: no nations in queue, blocking")
                event.clear()
                await event.wait()

def parse_config(path: str):
    global config

    with open(path, 'r') as config_file:
        data = json.load(config_file)
        config.client = data["client"]
        if config.client is None:
            print("Invalid configuration file!")
            sys.exit(1)

        for key, value in data.items():
            if key != "client":
                if type(value) != list:
                    print("Invalid configuration file!")
                    sys.exit(1)

                config.templates[key] = [TGTemplate(v["tgid"], v["key"]) for v in value]

def main() -> None:
    parser = argparse.ArgumentParser(prog="moonlark-api", description="Moonlark API recruitment script")
    parser.add_argument("-n", "--nation-name", required=True)
    parser.add_argument("config_file")
    args = parser.parse_args()

    parse_config(args.config_file)

    user_agent = sans.set_agent(f"Moonlark/{VERSION} (API script) by Merethin, used by {args.nation_name}")
    print(f"User agent set to {user_agent}")

    if not util.check_if_nation_exists(args.nation_name):
        print(f"The nation {args.nation_name} does not exist. Try again.")
        sys.exit(1)

    event = asyncio.Event()

    coroutines = [
        sse_loop(event),
        telegram_loop(event),
    ]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.gather(*coroutines))

if __name__ == "__main__":
    main()