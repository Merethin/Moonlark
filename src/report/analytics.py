import sqlite3, time
from .classes import Telegram, Analytics, Nation
from progress.bar import ChargingBar

def format_database_data(data) -> Nation:
    return Nation(data[0], data[1], data[2], data[3], data[4])

def query_nation(cursor: sqlite3.Cursor, name: str) -> Nation | None:
    cursor.execute("SELECT * FROM nations WHERE api_name = ?", [name])
    data = cursor.fetchone()

    if data is None:
        return None

    return format_database_data(data)

def canonName(cursor: sqlite3.Cursor, nation: str):
    return query_nation(cursor,nation).canon_name

DAY = 60 * 60 * 24

def time_since_last_active(nation: Nation) -> float:
    return time.time() - nation.lastlogin

def generate_analytics(cur: sqlite3.Cursor, telegram: Telegram, region: str, inactivity_threshold: int = 7) -> Analytics:
    analytics = Analytics.empty()

    analytics.stats = telegram.stats
    analytics.timeRange = telegram.timeRange

    print(f"D: Generating analytics for recruits of template {telegram.category}")

    with ChargingBar('Generating', max=len(telegram.recruits)) as bar:
        for nation, data in telegram.recruits.items():
            if data.cte:
                bar.next()
                continue

            nation_data = query_nation(cur, nation)
            if nation_data:
                if nation_data.region == region:
                    if time_since_last_active(nation_data) < (DAY * inactivity_threshold):
                        analytics.faithful.append(data)

                        if nation_data.wa:
                            analytics.wa_faithful.append(data)
                else:
                    if nation_data.region not in analytics.traitor_destinations.keys():
                        analytics.traitor_destinations[nation_data.region] = 0
                    
                    analytics.traitor_destinations[nation_data.region] += 1

            bar.next()

    print(f"E: Generating analytics for non-recruited recipients of template {telegram.category}")

    with ChargingBar('Generating', max=len(telegram.recipients)) as bar:
        for nation in telegram.recipients:
            if nation in telegram.recruits.keys():
                bar.next()
                continue

            nation_data = query_nation(cur, nation)
            if nation_data and nation_data.region != region:
                if nation_data.region not in analytics.uninterested_destinations.keys():
                    analytics.uninterested_destinations[nation_data.region] = 0
                    
                analytics.uninterested_destinations[nation_data.region] += 1
            
            bar.next()

    return analytics