from .classes import Recruit, Telegram, TelegramTemplate, TimeRange, Stats
import json, os

def import_raw_template_data(path: str):
    with open(path, "r") as tgdata:
        return json.load(tgdata)
    
def import_template_data(path: str):
    tgdata = import_raw_template_data(path)

    template = TelegramTemplate()
    template.tgid = tgdata["tgid"]
    template.type = tgdata["type"]
    template.nation = tgdata["nation"]
    template.category = tgdata.get("category", "Uncategorized")
    template.timeRange = TimeRange(tgdata["createdAt"], tgdata["generatedAt"])
    template.stats = Stats(tgdata["delivered"], tgdata.get("readCount", 0), tgdata["recruitCount"])
    template.recipients = tgdata["recipients"]
    template.recruits = {}
    for recruit in tgdata["recruits"]:
        template.recruits[recruit["name"]] = Recruit(recruit["cte"], recruit["timestamp"], recruit["name"])

    return template

def create_empty_telegram(category_name: str) -> Telegram:
    telegram = Telegram()
    telegram.category = category_name
    telegram.stats = Stats.empty()
    telegram.timeRange = TimeRange.default()
    telegram.recipients = []
    telegram.recruits = {}
    telegram.templates = []
    telegram.methods = {}
    telegram.nations = {}

    return telegram

def parse_template_folder(path: str) -> dict[str, Telegram]:
    telegrams: dict[str, Telegram] = {}

    for entry in os.scandir(path):
        if entry.is_file() and entry.name.endswith(".json"):
            template = import_template_data(entry.path)

            if template.category not in telegrams.keys():
                telegrams[template.category] = create_empty_telegram(template.category)

            telegram = telegrams[template.category]

            telegram.stats.add(template.stats)

            telegram.recipients += template.recipients
            telegram.recruits.update(template.recruits)

            telegram.timeRange.try_add_start(template.timeRange.start)
            telegram.timeRange.try_add_end(template.timeRange.end)

            if template.type not in telegram.methods.keys():
                telegram.methods[template.type] = Stats.empty()

            if template.nation not in telegram.nations.keys():
                telegram.nations[template.nation] = Stats.empty()

            telegram.methods[template.type].add(template.stats)
            telegram.nations[template.nation].add(template.stats)

            telegram.templates.append(template)

    return telegrams