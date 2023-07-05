from discord.ext import tasks, commands
import requests
import asyncio
from datetime import datetime, timedelta
import pytz
import json
import re
import logging

swBot = None
PREFIX = '♂'

def setup(outerBot: commands.Bot, prefix: str) -> commands.bot:
    global swBot
    global PREFIX

    PREFIX = prefix
    swBot = outerBot

    asyncio.run(swBot.add_cog(ArbitrationCog(swBot)))

class ArbitrationCog(commands.Cog, name='aritrationCog'):

    LINK_FOR_REQUEST = r'https://api.warframestat.us/pc/arbitration'

    LIST_OF_IMPORTANT_EVENT = (
        'Hydron (Sedna)',
        'Casta (Ceres)',
        'Helene (Saturn)',
        'Odin (Mercury)',
        'Cinxia (Ceres)',
        'Seimeni (Ceres)',
        'Sechura (Pluto)'
    )

    def __init__(self, clinet: commands.Bot) -> None:

        self.bot = clinet
        self.__timeNextArbitraion = None

    @commands.Cog.listener()
    async def on_ready(self):

        with open('resource/data.json', encoding='utf8') as dataFile:
            data: dict[str, any] = json.load( dataFile )

            if 'guild_id' in data.keys():

                self.__guild = self.bot.get_guild(data['guild_id'])

                if 'arbitration_channel' in data.keys():
                    self.__arbitrationChannel = self.__guild.get_channel(data['arbitration_channel'])
                else:
                    self.__arbitrationChannel = None

                self.__updateArbitrationChannel()

            else:
                raise NameError('Guild is not set')
            
        if self.__arbitrationChannel:
            self.alertArbitration.start()

    @tasks.loop( minutes = 1.0 )
    async def alertArbitration(self):
        try:
        
            if (self.__timeNextArbitraion is None or datetime.now(pytz.UTC).replace(tzinfo=pytz.UTC) >= self.__timeNextArbitraion) and self.__arbitrationChannel:

                respond = requests.get(self.LINK_FOR_REQUEST)

                if respond.status_code != 200:
                    self.__timeNextArbitraion = None
                    return
                
                dataDict = respond.json()

                if not ('expiry' in dataDict or 'activation' in dataDict or 'node' in dataDict or 'type' in dataDict or 'enemy' in dataDict):
                    return

                tempTime = datetime.strptime(dataDict['expiry'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC)

                if tempTime == self.__timeNextArbitraion: return

                self.__timeNextArbitraion = tempTime
                

                timeStartArbitraion = (datetime.strptime(dataDict['activation'], '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(hours=3)).strftime("%H:%M:%S")
                timeFinishArbitraion = (datetime.strptime(dataDict['expiry'], '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(hours=3)).strftime("%H:%M:%S")

                alertMessage = f'{timeStartArbitraion}-{timeFinishArbitraion} {dataDict["node"]}, {dataDict["type"]} {dataDict["enemy"]}'

                if dataDict["node"] in self.LIST_OF_IMPORTANT_EVENT:
                    alertMessage = '@everyone ' + alertMessage

                await self.__arbitrationChannel.send(alertMessage)

        except Exception as e: 
            logging.info(str(e))

    @commands.command(name = 'setARC')
    async def setArbitrationChannel(self, ctx: commands.Context, id: int | str = None, *_):
        
        if id is None:
            self.__arbitrationChannel = None
            self.alertArbitration.stop()
            await ctx.send('Канал удалён')
            self.__updateArbitrationChannel()
            return
        
        if type(id) is str:
            if re.match(r'^<#\d{10,20}>$', id):
                id = int(id[2:-1])

        if type(id) is not int:
            await ctx.send('Упс, не вышло')
            return
        
        self.__arbitrationChannel = self.__guild.get_channel(id)

        if self.__arbitrationChannel is None:
            await ctx.send('Упс, не вышло')
            return

        await ctx.send(f'Установлен {self.__arbitrationChannel.mention}')
        self.alertArbitration.start()
        self.__updateArbitrationChannel()

    def __updateArbitrationChannel(self):

        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            data["arbitration_channel"] = None if self.__arbitrationChannel is None else self.__arbitrationChannel.id
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)