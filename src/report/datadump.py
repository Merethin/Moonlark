import os, gzip, requests, sqlite3
import xml.etree.ElementTree as ET
from .filters import normalizeNationName

def download_nation_data_dump(nation: str) -> None:
    url = 'https://www.nationstates.net/pages/nations.xml.gz'
    headers = {'Accept': 'application/gzip', 'User-Agent': f"Moonlark (report generator) by Merethin, used by {nation}"}

    print(f"Downloading data dump from {url}")
    print(f"Headers = {headers}")

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open("nations.xml.gz", 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    with gzip.open("nations.xml.gz", 'rb') as f:
        file_content = f.read()
        with open("nations.xml", 'wb') as output:
            output.write(file_content)
    
    os.remove("nations.xml.gz")

# Extract nation data from the nations.xml data dump.
def parse_nation_data(filename: str) -> list[tuple]:
    tree = ET.parse(filename)
    root = tree.getroot()

    nation_data = []

    nations = root.findall("./NATION")

    for nation in nations:
        canon_name = nation.find("NAME").text
        api_name = normalizeNationName(canon_name)
        region = normalizeNationName(nation.find("REGION").text)
        wa = False
        if nation.find("UNSTATUS").text == "WA Member":
            wa = True
        lastlogin = int(nation.find("LASTLOGIN").text)

        nation_data.append((canon_name, api_name, region, wa, lastlogin))

    return nation_data

# Generate the nation information database, using the provided nation name (user agent) to identify itself to NationStates.
def generate_database(ua: str, download: bool = True) -> sqlite3.Connection:
    if download:
        if os.path.exists("nations.db"):
            os.remove("nations.db")

    con = sqlite3.connect("nations.db")

    if download:
        cursor = con.cursor()
        cursor.execute("CREATE TABLE nations(canon_name, api_name, region, wa, lastlogin)")

        download_nation_data_dump(ua)
        nation_data = parse_nation_data("nations.xml")

        cursor.executemany("INSERT INTO nations VALUES(?, ?, ?, ?, ?)", nation_data)
        con.commit()

    return con