import jinja2, os, json, argparse
from src.report.datadump import generate_database
from src.report.parse import parse_template_folder
from src.report.filters import renderDate, items, sortByHighest, sortStatsByHighest, sortTop, sortStatsTop, methodName, displayNumberWithCommas
from src.report.analytics import generate_analytics, canonName
from src.report.classes import Analytics, accumulate, Stats, Telegram

class MoonlarkEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return super().default(o)
        except TypeError:
            if type(o) == list:
                return o
            return o.__dict__
        
def main():
    parser = argparse.ArgumentParser(prog="genreport", description="Moonlark recruitment report generator")
    parser.add_argument("-n", "--nation-name", default="", help="Main nation of the player using this script")
    parser.add_argument("-r", "--regenerate", action='store_true', help="Whether to re-download the data dump or use the existing one")
    parser.add_argument("-a", "--activity-threshold", default=7, type=int, help="The number of days to use as the activity threshold for 'faithful players'. Default: 1 week (7 days).")
    parser.add_argument("--region", required=True, help="The region to generate statistics for.")
    parser.add_argument("-o", "--output", default="reports", help="The folder in which to store the generated files. Defaults to 'reports'. It is recommended to create a new subfolder in this directory for each report.")
    parser.add_argument("-i", "--input", help="If provided, will not generate a new report and will format the existing JSON report as HTML files.")
    parser.add_argument("-t", "--tg-source", default="telegrams", help="The folder to search for telegram template data. Defaults to 'telegrams'.")
    args = parser.parse_args()

    nation_name = ""

    if len(args.nation_name) != 0:
        nation_name = args.nation_name
    else:
        nation_name = input("Please enter your main nation name: ")

    print("A: Downloading data dump and creating database")

    con = generate_database(nation_name, args.regenerate)
    cursor = con.cursor()

    folder = args.output
    os.makedirs(folder, exist_ok=True)

    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
    env.filters['renderdate'] = renderDate
    env.filters['items'] = items
    env.filters['sorttop'] = sortTop
    env.filters['sortstatstop'] = sortStatsTop
    env.filters['sortbyhighest'] = sortByHighest
    env.filters['sortstatsbyhighest'] = sortStatsByHighest
    env.filters['methodname'] = methodName
    env.filters['canonname'] = lambda nation: canonName(cursor, nation)
    env.filters['displaynum'] = displayNumberWithCommas

    tgtemplate = env.get_template("telegram.html.jinja")

    print("B: Parsing telegram template data")

    telegrams = {}

    overall_analytics = Analytics.empty()
    overall_methods = {}
    overall_nations = {}

    if args.input: # Deserialize everything from input
        input_json = None
        with open(args.input, "r") as input_file:
            input_json = json.load(input_file)

        overall_analytics = Analytics.fromJSON(input_json["analytics"])
        overall_methods = input_json["methods"]
        overall_nations = input_json["nations"]

        for k, v in overall_methods.items():
            overall_methods[k] = Stats.fromJSON(v)

        for k, v in overall_nations.items():
            overall_nations[k] = Stats.fromJSON(v)

        telegrams = input_json["telegrams"]

        for k, v in telegrams.items():
            telegrams[k] = Telegram.fromJSON(v)

        print("C-F: Skipping all steps by loading data from JSON")
    
    else: # 10-minute-long computation yaay
        telegrams = parse_template_folder(args.tg_source)

        for category, telegram in telegrams.items():
            print(f"C: Generating analytics for template {category}")
            telegram.analytics = generate_analytics(cursor, telegram, args.region, args.activity_threshold)

            print(f"F: Adding analytics for template {category} to overall analytics")
            overall_analytics.add(telegram.analytics)

            overall_methods = accumulate(overall_methods, telegram.methods, Stats.empty(), lambda base,other: base.join(other))
            overall_nations = accumulate(overall_nations, telegram.nations, Stats.empty(), lambda base,other: base.join(other))

    print(f"G: Generating final report as HTML and JSON")

    json_output = {}
    json_output["methods"] = overall_methods
    json_output["nations"] = overall_nations
    json_output["analytics"] = overall_analytics
    json_output["telegrams"] = telegrams
    with open(f"{folder}/report.json", "w") as output:
        json.dump(json_output, fp=output, indent=4, cls=MoonlarkEncoder)

    for category, telegram in telegrams.items():
        result = tgtemplate.render(telegram=telegram)

        with open(f"{folder}/{category}.html", "w") as output:
            output.write(result)

    index_template = env.get_template("index.html.jinja")
    result = index_template.render(analytics=overall_analytics, methods=overall_methods, nations=overall_nations, telegrams=telegrams)

    with open(f"{folder}/index.html", "w") as output:
        output.write(result)

    print(f"H: HTML report saved in {folder}/index.html, JSON report saved in {folder}/report.json")

if __name__ == "__main__":
    main()