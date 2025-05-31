from discord.ext import commands
import sqlite3

class Database(commands.Cog):
    def __init__(self, bot: commands.Bot, connection: sqlite3.Connection):
        self.bot = bot
        self.db = connection