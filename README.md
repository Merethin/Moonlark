<h1 style="text-align: center;">Moonlark</h1>

<i style="text-align: center;">

You know, we weren't exactly expecting to receive the news from a bird.

Hm, not the fanciest tech around. One would think Bigtopia would put more effort into their communications.

That's the thing, somehow they seem to be gaining more new recruits than we have lately.

Must be no ordinary bird, then...

</i>

<p style="text-align: center;">
Welcome to <b>Moonlark</b> - the bird that delivers your NationStates recruitment telegrams.</p>

<p style="text-align: center;">
<b>Moonlark</b> is an all-in-one suite for NS recruitment - including two recruitment clients, one API script and one Discord bot for manual telegramming - both powered by server-sent events to deliver your telegrams almost as soon as nations are founded, with puppet filtering so that you can telegram the nations that actually matter.
</p>

<p style="text-align: center;">
With little effort on your part (besides writing the telegrams), Moonlark will mix and match as many templates as you can throw at it - three for new WA joins, three for newly founded nations, and three for refounds? No problem, both the API and manual clients will alternate between templates depending on the nation's origin, providing A/B telegram testing by default.
</p>

<p style="text-align: center;">
Moonlark also incorporates an analytics tool that lets you access more statistics than the ones displayed on the website, and compare statistics across all templates you're using, to get insights into how your telegrams are doing and what could be improved.
</p>

<i style="text-align: center;">

It is unclear how useful telegram A/B testing is exactly, but hey, if you want the feature, it's there, what else can I tell you :P

</i>

<p style="text-align: center;">
And of course, Moonlark is completely free and open-source software, released under a permissive license.
</p>

## Installation

Get Python, preferably the latest version (3.13.3)

Create a virtual environment (`python -m venv venv`), enter it (`source venv/bin/activate`) and install the requirements (`pip install -r requirements.txt`).

## Configuration

For the Discord bot, you'll want to create an app on the developer dashboard, and then paste the token into `.env`:

`TOKEN = "[REDACTED]"`

For the API script, you'll want to create a JSON file, naming it `api.json` for example, with the following format:

```
{
    "client": "[CLIENT-KEY]",
    "wa": [
        {
            "tgid": XXXXXXXX,
            "key": "[SECRET-KEY-X]"
        }
    ],
    "newfound": [
        {
            "tgid": YYYYYYYY,
            "key": "[SECRET-KEY-Y]"
        }
    ],
    "refound": [
        {
            "tgid": ZZZZZZZZ,
            "key": "[SECRET-KEY-Z]"
        }
    ]
}
```

The `client` key is the API key that's obtained when contacting the NationStates mods.

Each telegram, when sent to `tag:template` (make sure to check the recruitment box), will give you a template ID and a secret key, those are the `tgid` and `key` fields respectively.

As an example, there's one template per category, but you can add more.

New WA joins will get one random telegram from the `wa` category.

Newfounds will get one random telegram from the `newfound` category.

Refounded nations will get one random telegram from the `refound` category.

You can reuse the same telegram across multiple categories, if you don't feel like writing different telegrams.

## Usage

### Discord bot:

`python manual.py -n [YOUR_NATION_NAME]`

Whenever the bot joins a guild for the first time, the server owner must run `/config` to configure it.

`/add` will add a telegram template (`destination` being one of `wa`, `newfound` or `refound`). `category` is a name you can use for whatever purpose - usually each identical template will have the same category. You can use `/remove` to remove all registered templates matching a specific category.

Alternatively, running `/setup` will simply add a "generic" template for all three destinations. This is the preferred command to use if you don't want to use multiple templates and/or change templates depending on whether the nation being recruited is a new WA join, newfound or refound. And it's easier to explain to your new recruiters.

You can view registered templates for you in a specific guild by running `/templates` or clear them with `/clear`.

When your templates are set up, run `/recruit [DELAY]` with the delay between telegrams. This will depend on your nation age - younger nations may need up to a 2 minute cooldown, while older ones can conform themselves with 1 minute. There is a Dot command to check this (`/timer`). 

Optionally, you can also provide a container name, if you use Containerise and want to send telegrams from a nation that isn't your main. Telegram links will automatically open in said container.

To end the recruitment session, run `/stop`. 

To view recruitment stats for your server, run `/stats`. By default the command will show all-time statistics, but by passing a number `X` to the `since` parameter, it will show stats for the last `X` days.

People recruiting in the same server are assumed to be recruiting for the same region, and therefore nations are distributed between them.

### API script:

`python api.py -n [YOUR_NATION_NAME] api.json`

After you've configured the API settings in `api.json`, this is all you have to do.

### Report generation:

`python genreport.py -n [YOUR_NATION_NAME] --region [YOUR_REGION_NAME]`

A full list of flags can be found by running `python genreport.py --help`.

To get the statistics from each of the telegram templates used in your campaign, you'll need to use [masstgexport.user.js](masstgexport.user.js) with an extension like Tampermonkey. Navigating to a telegram page on NS will give you options to download telegram statistics as a JSON file.

Ask all of your recruiters to do this, using the links given by Moonlark using the `/templates` command (which include the category in the URL). Once you have all the JSON files, place them in `telegrams/` and run the report.

After a _while_, both HTML and JSON will be generated in the output folder. The report will be viewable in `index.html`, and saved in `report.json` which can later be imported with `-i`.

### To-do/Unimplemented

- Polish up the reports, especially the UI, and include additional data