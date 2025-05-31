from dataclasses import dataclass
from .filters import renderRate

def accumulate(dest: dict, src: dict, default, add_callback) -> dict:
    result = {}
    result.update(dest)

    for element, value in src.items():
        if element not in result.keys():
            result[element] = default
        result[element] = add_callback(result[element],value)

    return result

@dataclass
class Recruit:
    cte: bool
    recruitedAt: int
    name: str

    @staticmethod
    def fromJSON(src: dict):
        return Recruit(src["cte"], src["recruitedAt"], src["name"])

@dataclass
class Nation:
    canon_name: str
    api_name: str
    region: str
    wa: bool
    lastlogin: int

@dataclass
class Stats:
    delivered: int
    readCount: int
    recruitCount: int

    def add(self, other):
        self.delivered += other.delivered
        self.readCount += other.readCount
        self.recruitCount += other.recruitCount

    def join(self, other):
        result = Stats.empty()

        result.delivered = self.delivered + other.delivered
        result.readCount = self.readCount + other.readCount
        result.recruitCount = self.recruitCount + other.recruitCount

        return result

    @property
    def readRate(self):
        return renderRate(self.delivered, self.readCount)
    
    @property
    def recruitRate(self):
        return renderRate(self.delivered, self.recruitCount)
    
    @property
    def readToRecruitRate(self):
        return renderRate(self.readCount, self.recruitCount)

    @staticmethod
    def empty():
        return Stats(0, 0, 0)
    
    @staticmethod
    def fromJSON(src: dict):
        return Stats(src["delivered"], src["readCount"], src["recruitCount"])
    
@dataclass
class TimeRange:
    start: int
    end: int

    @staticmethod
    def default():
        return TimeRange(9999999999999, 0)
    
    def try_add_start(self, start: int):
        if start < self.start:
            self.start = start

    def try_add_end(self, end: int):
        if end > self.end:
            self.end = end
    
    @staticmethod
    def fromJSON(src: dict):
        return TimeRange(src["start"], src["end"])

@dataclass
class Analytics:
    stats: Stats
    faithful: list[Recruit]
    wa_faithful: list[Recruit]
    traitor_destinations: dict[str, int]
    uninterested_destinations: dict[str, int]
    timeRange: TimeRange

    @property
    def faithfulCount(self):
        return len(self.faithful)
    
    @property
    def waFaithfulCount(self):
        return len(self.wa_faithful)

    @staticmethod
    def empty():
        return Analytics(Stats.empty(), [], [], {}, {}, TimeRange.default())
    
    def add(self, other):
        self.faithful += other.faithful
        self.wa_faithful += other.wa_faithful
        self.stats.add(other.stats)

        self.timeRange.try_add_start(other.timeRange.start)
        self.timeRange.try_add_end(other.timeRange.end)

        self.traitor_destinations = accumulate(self.traitor_destinations, other.traitor_destinations, 0, lambda a, b: a+b)
        self.uninterested_destinations = accumulate(self.uninterested_destinations, other.uninterested_destinations, 0, lambda a, b: a+b)

    @property
    def preserveRate(self):
        return renderRate(self.stats.recruitCount, len(self.faithful))
    
    @property
    def waPreserveRate(self):
        return renderRate(self.stats.recruitCount, len(self.wa_faithful))
    
    @staticmethod
    def fromJSON(src: dict):
        return Analytics(Stats.fromJSON(src["stats"]), [Recruit.fromJSON(s) for s in src["faithful"]], [Recruit.fromJSON(s) for s in src["wa_faithful"]], src["traitor_destinations"], src["uninterested_destinations"], TimeRange.fromJSON(src["timeRange"]))

class TelegramTemplate:
    tgid: int
    type: str
    nation: str
    category: str
    timeRange: TimeRange
    stats: Stats
    recipients: list[str]
    recruits: dict[str, Recruit]

    @staticmethod
    def fromJSON(src: dict):
        tgtemplate = TelegramTemplate()
        tgtemplate.tgid = src["tgid"]
        tgtemplate.type = src["type"]
        tgtemplate.nation = src["nation"]
        tgtemplate.category = src["category"]
        tgtemplate.timeRange = TimeRange.fromJSON(src["timeRange"])
        tgtemplate.stats = Stats.fromJSON(src["stats"])
        tgtemplate.recipients = src["recipients"]
        tgtemplate.recruits = src["recruits"]

        for k, v in tgtemplate.recruits.items():
            tgtemplate.recruits[k] = Recruit.fromJSON(v)

        return tgtemplate

class Telegram:
    stats: Stats
    category: str
    recipients: list[str]
    recruits: dict[str, Recruit]
    templates: list[TelegramTemplate]
    methods: dict[str, Stats]
    nations: dict[str, Stats]
    timeRange: TimeRange
    analytics: Analytics

    @staticmethod
    def fromJSON(src: dict):
        tg = Telegram()
        tg.stats = Stats.fromJSON(src["stats"])
        tg.category = src["category"]
        tg.recipients = src["recipients"]
        tg.recruits = src["recruits"]

        for k, v in tg.recruits.items():
            tg.recruits[k] = Recruit.fromJSON(v)

        tg.templates = [TelegramTemplate.fromJSON(s) for s in src["templates"]]

        tg.methods = src["methods"]
        tg.nations = src["nations"]

        for k, v in tg.methods.items():
            tg.methods[k] = Stats.fromJSON(v)

        for k, v in tg.nations.items():
            tg.nations[k] = Stats.fromJSON(v)

        tg.timeRange = TimeRange.fromJSON(src["timeRange"])
        tg.analytics = Analytics.fromJSON(src["analytics"])

        return tg