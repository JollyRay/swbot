from discord.ext import commands, tasks
from discord import Embed, File, Message, TextChannel, Color
import asyncio
from discordPart.cog.patrenCog import SWStandartCog
from time import time
import json
import logging
import traceback

swBot = None
PREFIX = '♂'

def setup(outerBot: commands.Bot, prefix: str) -> commands.bot:
    global swBot
    global PREFIX

    PREFIX = prefix
    swBot = outerBot

    asyncio.run(swBot.add_cog(DuviriCog(swBot)))

class DuviriCog(SWStandartCog, name='duviriCog'):

    DUVIRI_STATE: list[dict] = [
        {'name': 'Печаль', 'color': 0xA0A0A0, 'role': None},
        {'name': 'Страх', 'color': 0x004040, 'role': None},
        {'name': 'Радость', 'color': 0xA0F000, 'role': None},
        {'name': 'Ярость', 'color': 0xf00000, 'role': None},
        {'name': 'Зависть', 'color': 0x007000, 'role': None}
    ]

    STATE_DURATION = 2 * 60 * 60
    ALL_STATE_DURATION = STATE_DURATION * len(DUVIRI_STATE)
    BASE_TIME_TO_WAIT = 60

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.stateNextTime = None

        self.__guild = None
        self.__duviriChannel: TextChannel | None = None
        self.__duviriMessage: Message | None = None

    @commands.Cog.listener()
    async def on_ready(self):

        with open('resource/data.json', encoding='utf8') as dataFile:
            data: dict[str, any] = json.load( dataFile )

            if 'guild_id' in data.keys():
                self.__guild = self.bot.get_guild(data['guild_id'])
            else:
                raise NameError('Guild is not set')

            if 'alerts' in data.keys() and 'duviri' in data['alerts']:

                if 'channel' in data['alerts']['duviri'] and data['alerts']['duviri']['channel'] is not None:
                    self.__duviriChannel = self.__guild.get_channel(data['alerts']['duviri']['channel'])

                    if 'message' in data['alerts']['duviri'] and data['alerts']['duviri']['message'] is not None:
                        self.__duviriMessage = await self.__duviriChannel.fetch_message(data['alerts']['duviri']['message'])

                
                if len(self.DUVIRI_STATE) > 0 and 'sad_role' in data['alerts']['duviri'] and data['alerts']['duviri']['sad_role'] is not None:
                    self.DUVIRI_STATE[0]['role'] = self.__guild.get_role(data['alerts']['duviri']['sad_role'])
                if len(self.DUVIRI_STATE) > 1 and 'fear_role' in data['alerts']['duviri'] and data['alerts']['duviri']['fear_role'] is not None:
                    self.DUVIRI_STATE[1]['role'] = self.__guild.get_role(data['alerts']['duviri']['fear_role'])
                if len(self.DUVIRI_STATE) > 2 and 'joy_role' in data['alerts']['duviri'] and data['alerts']['duviri']['joy_role'] is not None:
                    self.DUVIRI_STATE[2]['role'] = self.__guild.get_role(data['alerts']['duviri']['joy_role'])
                if len(self.DUVIRI_STATE) > 3 and 'rage_role' in data['alerts']['duviri'] and data['alerts']['duviri']['rage_role'] is not None:
                    self.DUVIRI_STATE[3]['role'] = self.__guild.get_role(data['alerts']['duviri']['rage_role'])
                if len(self.DUVIRI_STATE) > 4 and 'envy_role' in data['alerts']['duviri'] and data['alerts']['duviri']['envy_role'] is not None:
                    self.DUVIRI_STATE[4]['role'] = self.__guild.get_role(data['alerts']['duviri']['envy_role'])

            self.__updateAlertData()

        ######################
        #                    #
        #     START LOOP     #
        #                    #
        ######################    

        if not self.duviriLoop.is_running():
            self.duviriLoop.start()
        else:
            self.duviriLoop.restart()

    @tasks.loop( count = 1 )
    async def duviriLoop(self):
        try:
            while True:
                timeForWita = await self.alertDuviri()
                await asyncio.sleep(timeForWita)
        except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
            pass

    async def alertDuviri(self):
        try:

            timeNow = time()
            if self.stateNextTime is not None and self.stateNextTime > timeNow:
                return max(self.BASE_TIME_TO_WAIT, self.stateNextTime - timeNow)
            
            if self.__duviriChannel is not None:
                
                self.stateNextTime = int( time() - ( time() % self.STATE_DURATION) + self.STATE_DURATION )
                stateNumber = int( time() % self.ALL_STATE_DURATION // self.STATE_DURATION )
                embed = self.__composeDuviriEmbed( stateNumber )
                image = File(f'resource/alert/mask{stateNumber}.png', filename='image.png')

                if self.__duviriMessage is None:
                    self.__duviriMessage = await self.__duviriChannel.send(embed = embed, file = image)
                    self.__updateAlertData()
                else:
                    await self.__duviriMessage.edit( embed = embed, attachments = [image] )

                await self.__duviriChannel.send(
                    f'{self.DUVIRI_STATE[stateNumber]["name"] if self.DUVIRI_STATE[stateNumber]["role"] is None else self.DUVIRI_STATE[stateNumber]["role"].mention} Конец: <t:{self.stateNextTime}:R>',
                    delete_after = max(self.BASE_TIME_TO_WAIT, self.stateNextTime - time())
                )
                
                return max(self.BASE_TIME_TO_WAIT, self.stateNextTime - time())
            
        except: 
            logging.info(traceback.format_exc())

        return self.BASE_TIME_TO_WAIT

    def __composeDuviriEmbed(self, stateId: int) -> Embed:

        if stateId >= len(self.DUVIRI_STATE):
            return None
        
        timeStart = int( time() - ( time() % self.ALL_STATE_DURATION ) )

        content = ''

        for stateIndex in range(len(self.DUVIRI_STATE)):
            stateTime = timeStart + self.STATE_DURATION * ( stateIndex + 1)
            content += f'\n{self.DUVIRI_STATE[ ( stateIndex + stateId + 1) % len(self.DUVIRI_STATE) ]["name"]}: <t:{stateTime}:R>'

        embed = Embed(
            color = self.DUVIRI_STATE[stateId]['color'] if self.DUVIRI_STATE[stateId]['role'] is None else self.DUVIRI_STATE[stateId]['role'].color,
            title = f'Сейчас - {self.DUVIRI_STATE[stateId]["name"]}',
            description = content,
        )
        embed.set_thumbnail(url='attachment://image.png')

        return embed

    def __updateAlertData(self):
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            data["alerts"]['duviri'] = {
                "channel": None if self.__duviriChannel is None else self.__duviriChannel.id,
                "message": None if self.__duviriMessage is None else self.__duviriMessage.id
            }
            
            if len(self.DUVIRI_STATE) > 0:
                data["alerts"]['duviri']['sad_role'] =  None if self.DUVIRI_STATE[0]['role'] is None else self.DUVIRI_STATE[0]['role'].id
            if len(self.DUVIRI_STATE) > 1:
                data["alerts"]['duviri']['fear_role'] = None if self.DUVIRI_STATE[1]['role'] is None else self.DUVIRI_STATE[1]['role'].id
            if len(self.DUVIRI_STATE) > 2:
                data["alerts"]['duviri']['joy_role'] = None if self.DUVIRI_STATE[2]['role'] is None else self.DUVIRI_STATE[2]['role'].id
            if len(self.DUVIRI_STATE) > 3:
                data["alerts"]['duviri']['rage_role'] = None if self.DUVIRI_STATE[3]['role'] is None else self.DUVIRI_STATE[3]['role'].id
            if len(self.DUVIRI_STATE) > 4:
                data["alerts"]['duviri']['envy_role'] = None if self.DUVIRI_STATE[4]['role'] is None else self.DUVIRI_STATE[4]['role'].id
            
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)