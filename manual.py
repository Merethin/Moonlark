import discord, typing, sqlite3, sans, argparse, sys, asyncio
from discord.ext import commands
from dataclasses import dataclass
from dotenv import dotenv_values
import utility as util

from src.cogs.db import Database
from src.cogs.guilds import GuildManager
from src.cogs.template import TemplateManager
from src.cogs.nation import NationListener
from src.cogs.recruit import RecruitmentManager
from src.cogs.stats import StatsTracker

VERSION = "0.1.0"

class MoonlarkBot(commands.Bot):
    def __init__(self, connection: sqlite3.Connection, nation: str):
        intents: discord.Intents = discord.Intents.default()
        intents.members = True

        super().__init__(command_prefix="?", intents=intents)

        self.db_connection = connection
        self.nation = util.format_nation_or_region(nation)

    async def setup_hook(self):
        loop = asyncio.get_event_loop()
        loop.set_task_factory(asyncio.eager_task_factory)

        await self.add_cog(Database(self, self.db_connection))
        await self.add_cog(GuildManager(self))
        await self.add_cog(TemplateManager(self))
        await self.add_cog(RecruitmentManager(self, self.nation))
        await self.add_cog(NationListener(self))
        await self.add_cog(StatsTracker(self))

    async def on_ready(self):
        global nation_name
        print(f'Moonlark: logged in as {self.user}')

        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"Error syncing commands: {e}")


# Stores settings and templates for a guild.
@dataclass
class Guild:
    recruiters: list[typing.Awaitable[None]] # Currently active recruiters and their sessions

def create_tables_if_needed(connection: sqlite3.Connection):
    cursor = connection.cursor()

    table_list = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guilds'; ").fetchall()

    if table_list == []:
        # Guild list doesn't exist, create it
        cursor.execute("CREATE TABLE guilds(guild_id, admin_role_id, recruit_role_id, recruit_wa, recruit_newfounds, recruit_refounds)")
        cursor.execute("CREATE UNIQUE INDEX idx_guild_id ON guilds (guild_id);")
        connection.commit()

    user_templates_list = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_templates'; ").fetchall()

    if user_templates_list == []:
        # User templates list doesn't exist, create it
        cursor.execute("CREATE TABLE user_templates(unique_id, guild_id, user_id, wa, newfound, refound)")
        cursor.execute("CREATE UNIQUE INDEX idx_unique_id ON user_templates (unique_id);")
        connection.commit()

    stats_list = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stats'; ").fetchall()

    if stats_list == []:
        # Stats list doesn't exist, create it
        cursor.execute("CREATE TABLE stats(unique_id, guild_id, user_id, year, month, day, wa_sent, newfound_sent, refound_sent)")
        cursor.execute("CREATE UNIQUE INDEX idx_stat_unique_id ON stats (unique_id);")
        connection.commit()

    cursor.close()

def main() -> None:
    parser = argparse.ArgumentParser(prog="moonlark-manual", description="Moonlark manual recruitment bot")
    parser.add_argument("-n", "--nation-name", required=True)
    args = parser.parse_args()

    user_agent = sans.set_agent(f"Moonlark/{VERSION} (Discord bot) by Merethin, used by {args.nation_name}")
    print(f"User agent set to {user_agent}")

    if not util.check_if_nation_exists(args.nation_name):
        print(f"The nation {args.nation_name} does not exist. Try again.")
        sys.exit(1)

    connection = sqlite3.connect("bot.db")
    create_tables_if_needed(connection)

    bot = MoonlarkBot(connection, args.nation_name)

    settings = dotenv_values(".env")
    bot.run(settings["TOKEN"])

if __name__ == "__main__":
    main()