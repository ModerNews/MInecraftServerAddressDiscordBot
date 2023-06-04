import requests
import discord
import datetime, time
import logging
import os

from discord.ext import commands
from discord.ext.tasks import loop
from mcstatus import JavaServer


class ServerBot(commands.Bot):
    def __init__(self):

        # from configuration import bot_token, requestUri
        self._bot_token = __import__("configuration").bot_token
        self._requestUri = __import__("configuration").requestUri

        # del bot_token
        # del requestUri

        self.public_url = ""

        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, command_prefix="!")

    def start_bot(self):
        self.run(self._bot_token)

    async def on_ready(self):
        await self.add_cog(ServerCog(self))
        await self.tree.sync()
        try:
            self.setup_logging()
        except:
            logging.warning("Custom handler setup failed, falling back to default handler")
        # await bot.loop.create_task(status())

    def setup_logging(self):
        """
        Creates new file for log, and sets it as default log handler
        """
        from discord import utils

        if not os.path.exists('./logs'):
            os.mkdir('./logs')

        handler = logging.FileHandler(
            f"./logs/MinecraftServerStatus_{time.mktime(datetime.datetime.utcnow().timetuple())}.log", "a+")
        utils.setup_logging(handler=handler)

    def update_url(self):
        """
        Helper function to get current server IP from Ngrok

        :returns: None, updates class attribute
        """
        response = requests.get(self._requestUri).json()
        print(response)
        self.bot.public_url = response['tunnels'][0]['public_url'][6:]


class ServerCog(commands.Cog):
    def __init__(self, bot: ServerBot):
        self.bot: ServerBot = bot
        self.status.start()

    @loop(minutes=10)
    async def status(self):
        """
        Loop updating discord RPC for bot

        Gets current server status using
        """
        presence = ""  # Presence will be reseted every loop
        try:
            self.bot.update_url()
        except Exception:
            self.bot.public_url = None
        
        if self.bot.public_url is not None:
            try:
                server = JavaServer.lookup(self.bot.public_url)
                status = server.status()
                presence = f" {status.players.online} player(s) online, latency {round(status.latency, 2)} ms"
            except Exception:
                presence = "mcstatus not fetched 💀"
        
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=presence))

    @status.before_loop
    async def status_setup(self):
        """
        Wait for bot to startup before starting loop
        """
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name='get ip', description='Current ip of the minecraft server')
    async def getIp(self, ctx):
        """
        Command for getting servers current ip
        """
        try:
            self.bot.update_url()
            await ctx.send(self.bot.public_url, ephemeral=True)
        except Exception:
            await ctx.send("Failed miserably :skull:", ephemeral=True)


if __name__ == "__main__":
    bot = ServerBot()
    bot.start_bot()
