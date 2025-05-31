import datetime

def renderRate(total: int, count: int):
    rate = (count / total) * 100
    return f"{round(rate, 2)}%"

def renderDate(timestamp: int):
    local_date = datetime.date.fromtimestamp(timestamp)

    return local_date.strftime("%B %d, %Y")

def items(view: dict):
    return view.items()

def normalizeNationName(name: str):
    return name.lower().replace(" ", "_")

def methodName(method: str):
    methods = {
        "api": "API Template",
        "template": "Manual/Stamp Template",
        "generic": "Individual Mass TG",
    }

    return methods[method]

def sortByHighest(view: dict):
    return sorted(view.items(), key=lambda item: item[1], reverse=True)

def sortTop(view: dict):
    return sortByHighest(view)[:5]

def sortStatsByHighest(view: dict):
    return sorted(view.items(), key=lambda item: item[1].delivered, reverse=True)

def sortStatsTop(view: dict):
    return sortStatsByHighest(view)[:5]

def displayNumberWithCommas(number: int):
    return f'{number:,}'