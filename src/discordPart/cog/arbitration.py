import traceback
from discord.ext import tasks, commands
from discord import Embed, File, Message, Color
import requests
import asyncio
from datetime import datetime
import pytz
import json
import re
import logging
from discordPart.cog.patrenCog import SWStandartCog
from time import time
from asyncio import sleep
from utility.languageConver import planatTranslate, missionTypeTranslate, fractionTranslate

swBot = None
PREFIX = '♂'

def setup(outerBot: commands.Bot, prefix: str) -> commands.bot:
    global swBot
    global PREFIX

    PREFIX = prefix
    swBot = outerBot

    asyncio.run(swBot.add_cog(ArbitrationCog(swBot)))

class _SyndicateMissionStruct:
    def __init__(self, missionName: str, isSteel: bool, isCetus: bool, minLevel: int = 0, maxLevel: int = 0) -> None:
        self.missionName = missionName
        self.isSteel = isSteel
        self.isCetus = isCetus
        self.maxLevel = maxLevel
        self.minLevel = minLevel

class ArbitrationCog(SWStandartCog, name='aritrationCog'):

    LINK_FOR_REQUEST = r'https://10o.io/arbitrations.json'
    SPARE_LINK_FOR_REQUEST = r'https://10o.io/arbitrations.json'
    LINK_FOR_SYNDICATE = r'https://api.warframestat.us/pc/syndicateMissions/?language=ru'
    LINK_FOR_CETUS_TIME = r'https://api.warframestat.us/pc/cetusCycle/'

    BASE_TIME_TO_WAIT = 60
    SHORT_TIME_TOWAIT = 10

    # Color

    EIDOLON_COLOR = 0x7B917B
    AYA_COLOR = 0x007CFF
    ARBITRATION_COLOR = 0xE3256B
    FINISH_EVENT_COLOR = 0xF80000

    # Eidolon timers

    DAY_DURATION = 100 * 60
    NIGHT_DURATION = 50 * 60
    ALERT_EIDOLON_BEFORE = 10 * 60

    convertStrToTime = staticmethod(lambda stringTime: (datetime.strptime(stringTime, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC)))

    __extractRoleIdFromSting = staticmethod(lambda id: id if re.match(r'^<@&\d{10,20}>$', id) is None else int(id[3:-1]))

    LIST_OF_IMPORTANT_EVENT = (
        'Hydron (Седна)',
        'Casta (Церера)',
        'Helene (Сатурн)',
        'Odin (Меркурий)',
        'Cinxia (Церера)',
        'Seimeni (Церера)',
        'Sechura (Плутон)'
    )

    LIST_OF_IMPORTANT_VENUS_SYNDICATE_MISSION = (
        'отклонение и отвлечение',
        'охотник-убийца',
        'коллапс сети'
    )

    LIST_OF_IMPORTANT_CETUS_SYNDICATE_MISSION = (
        'найдите спрятанный артефакт',
        'захватите агента гринир'
    )

    def __init__(self, clinet: commands.Bot) -> None:

        self.bot = clinet
        self.__timeNextArbitraion = None
        self.__timeNextVenusSyndicate = None
        
        
        self.__eidolonChannel = None
        self.__arbitrationChannel = None
        self.__ayaChannel = None
        self.__eidolonRole = None
        self.__arbitrationRole = None
        self.__ayaRole = None

    @commands.Cog.listener()
    async def on_ready(self):

        with open('resource/data.json', encoding='utf8') as dataFile:
            data: dict[str, any] = json.load( dataFile )
            
            ######################
            #                    #
            #        GUILD       #
            #                    #
            ######################

            if 'guild_id' in data.keys():
                self.__guild = self.bot.get_guild(data['guild_id'])
            else:
                raise NameError('Guild is not set')

            ######################
            #                    #
            #     ALERT DATA     #
            #                    #
            ######################

            if 'alerts' in data.keys() and type(data.get('alerts')) is dict:

                if 'eidolon_channel' in data['alerts'].keys() and data['alerts']['eidolon_channel'] is not None:
                    self.__eidolonChannel = self.__guild.get_channel(data['alerts']['eidolon_channel'])

                if 'eidolon_role' in data['alerts'].keys() and data['alerts']['eidolon_role'] is not None:
                    self.__eidolonRole = self.__guild.get_role(data['alerts']['eidolon_role'])
                
                if 'arbitration_channel' in data['alerts'].keys() and data['alerts']['arbitration_channel'] is not None:
                    self.__arbitrationChannel = self.__guild.get_channel(data['alerts']['arbitration_channel'])

                if 'aya_channel' in data['alerts'].keys() and data['alerts']['aya_channel'] is not None:
                    self.__ayaChannel = self.__guild.get_channel(data['alerts']['aya_channel'])

                if 'arbitration_role' in data['alerts'].keys() and data['alerts']['arbitration_role'] is not None:
                    self.__arbitrationRole = self.__guild.get_role(data['alerts']['arbitration_role'])

                if 'aya_role' in data['alerts'].keys() and data['alerts']['aya_role'] is not None:
                    self.__ayaRole = self.__guild.get_role(data['alerts']['aya_role'])

            self.__updateAlertData()

        
        ######################
        #                    #
        #     START LOOP     #
        #                    #
        ######################    

        if not self.ayaLoop.is_running():
            self.ayaLoop.start()
        else:
            self.ayaLoop.restart()
        if not self.arbitrationLoop.is_running():
            self.arbitrationLoop.start()
        else:
            self.arbitrationLoop.restart()
        if not self.eidolonLoop.is_running():
            self.eidolonLoop.start()
        else:
            self.eidolonLoop.restart()

    @tasks.loop( count = 1 )
    async def eidolonLoop(self):
        while True:
            timeForWita = await self.alertEidolon()
            await sleep(timeForWita)

    async def alertEidolon(self):
        try:

            if self.__eidolonChannel is not None:

                respond = requests.get(self.LINK_FOR_CETUS_TIME)

                if respond.status_code != 200:
                    return self.BASE_TIME_TO_WAIT

                dataDict: dict = respond.json()

                if not ( 'isDay' in dataDict and 'expiry' in dataDict):
                    return self.BASE_TIME_TO_WAIT
                
                isDay = dataDict.get('isDay')
                timeEnd = self.convertStrToTime(dataDict.get('expiry')).timestamp()

                if not isDay or timeEnd - time() < self.ALERT_EIDOLON_BEFORE:
                    timeNightStart = None
                    timeNightEnd = None

                    if not isDay:
                        timeNightEnd = int(timeEnd)
                        timeNightStart = timeNightEnd - self.NIGHT_DURATION

                    if self.convertStrToTime(dataDict.get('expiry')).timestamp() - time() < self.ALERT_EIDOLON_BEFORE:
                        timeNightStart = int(timeEnd)
                        timeNightEnd = timeNightStart + self.NIGHT_DURATION

                    embed = self.__composeEidolonEmbed(timeNightStart, timeNightEnd)

                    image = File("resource/alert/eidolon.png", filename="image.png")
                    await self.__eidolonChannel.send(self.__eidolonRole.mention if self.__eidolonRole else "",
                                                    embed = embed, file = image)
                    
                    return timeNightEnd - time() + self.DAY_DURATION - self.ALERT_EIDOLON_BEFORE
                    
                return self.convertStrToTime(dataDict.get('expiry')).timestamp() - time() - self.ALERT_EIDOLON_BEFORE
        except: 
            logging.info(traceback.format_exc())

        return self.BASE_TIME_TO_WAIT

    def __composeEidolonEmbed(self, timeStart: int, timeFinish: int):

        embed = Embed(
            color = self.EIDOLON_COLOR,
            title = 'Эйдолоны - Ночь',
            description = f'''Начало: <t:{timeStart}:R>
Конец: <t:{timeFinish}:R>''',
        )
        embed.set_thumbnail(url='attachment://image.png')

        return embed

    @tasks.loop( count = 1 )
    async def arbitrationLoop(self):
        while True:
            timeForWita = await self.alertArbitration()
            await sleep(timeForWita)

    async def alertArbitration(self):
        try:
            if (self.__timeNextArbitraion is None or time() > self.__timeNextArbitraion) and self.__arbitrationChannel is not None:

                tempTime, mission, typeMission, fraction = self.arbitrationFindData()
                print(datetime.now().strftime("%H:%M:%S"), mission, typeMission, fraction)
                if tempTime is None:
                    return self.SHORT_TIME_TOWAIT
                
                self.__timeNextArbitraion = tempTime

                if mission in self.LIST_OF_IMPORTANT_EVENT:
                    embed = self.__composeArbitrationEmbed(tempTime, mission, typeMission, fraction)
                    image = File("resource/alert/arbitration.png", filename="image.png")
                    await self.__arbitrationChannel.send(self.__arbitrationRole.mention if self.__arbitrationRole else "",
                                                    embed = embed, file = image)
                
                return max(self.BASE_TIME_TO_WAIT, tempTime - time())
            
        except: 
            logging.info(traceback.format_exc())

        return self.BASE_TIME_TO_WAIT

    def __composeArbitrationEmbed(self, tempTime: int, mission: str, typeMission: str, fraction: str):

        embed = Embed(
            color = self.ARBITRATION_COLOR,
            title = f'{typeMission} - {fraction}',
            description = f'''{mission}
Уровни: 60-80
Конец: <t:{tempTime}:R>''',
        )
        embed.set_thumbnail(url='attachment://image.png')

        return embed

    def arbitrationFindData(self):

        '''

        Parameters
        ----------

        self


        Returns
        ----------        
        
        int
            Time in seconds when arbitration ends

        str
            Name of planet with mission's name

        str
            Mission type            

        str
            Name of fraction
        '''

        respond = requests.get(self.LINK_FOR_REQUEST)

        if respond.status_code == 200:

            dataDict: dict = respond.json()[0]

            if 'end' in dataDict and 'solnodedata' in dataDict and 'planet' in dataDict.get('solnodedata', {}) and 'tile' in dataDict.get('solnodedata', {}) and 'type' in dataDict.get('solnodedata', {}):
                tempTime = int(self.convertStrToTime(dataDict['end']).timestamp())
                tempTime -= tempTime % 3600

                if tempTime != self.__timeNextArbitraion:
                
                    return (
                        tempTime,
                        f'{dataDict["solnodedata"]["tile"]} ({planatTranslate.get(dataDict["solnodedata"]["planet"], dataDict["solnodedata"]["planet"])})',
                        missionTypeTranslate.get(dataDict['solnodedata']['type'], dataDict['solnodedata']['type']),
                        fractionTranslate.get(dataDict['solnodedata'].get('enemy', 'Any'), 'Кто-то точно есть')
                    )
            
        respond = requests.get(self.LINK_FOR_REQUEST)

        if respond.status_code == 200:
            

            dataDict: dict = respond.json()

            if 'expiry' in dataDict and 'node' in dataDict and 'type' in dataDict:
                
                tempTime = int(self.convertStrToTime(dataDict['expiry']).timestamp())
                tempTime -= tempTime % 3600

                if tempTime != self.__timeNextArbitraion:

                    nodeName: str = dataDict['node']

                    for engName, rusName in planatTranslate.items():
                        if nodeName.find(f'({engName})'):
                            nodeName = nodeName.replace(f'({engName})', f'({rusName})')
                            break

                    return (
                        tempTime,
                        nodeName,
                        missionTypeTranslate.get(dataDict['type'], dataDict['type']),
                        fractionTranslate.get(dataDict.get('enemy', 'Any'), 'Кто-то точно есть')
                    )
                    

        return (None, None, None, None)

    @tasks.loop( count = 1 )
    async def ayaLoop(self):
        while True:
            timeForWita = await self.alertAya()
            await sleep(timeForWita)

    async def alertAya(self):
        try:
            if (self.__timeNextVenusSyndicate is None or datetime.now(pytz.UTC).replace(tzinfo=pytz.UTC) > self.__timeNextVenusSyndicate) and self.__ayaChannel:

                respond = requests.get(self.LINK_FOR_SYNDICATE)
                
                if respond.status_code != 200:
                    return self.BASE_TIME_TO_WAIT
                
                listOfSyndicate: dict = respond.json()

                timeFinishAya, listOfImpotantSyndicateMission = self.__extractImpotantSyndicatMission(listOfSyndicate, self.__timeNextVenusSyndicate)
                
                if timeFinishAya is None:
                    return self.BASE_TIME_TO_WAIT
                
                self.__timeNextVenusSyndicate = timeFinishAya
                if listOfImpotantSyndicateMission is None:
                    return max(self.BASE_TIME_TO_WAIT, self.__timeNextVenusSyndicate.timestamp() - time())
                
                listOfMessageWithEmbed: list[Message] = []
                for syndicateData in listOfImpotantSyndicateMission:
                    ayaImage = File("resource/alert/aya.png", filename="image.png")
                    messageWithEmbed = await self.__ayaChannel.send(self.__ayaRole.mention if self.__ayaRole else "",
                                        embed = self.__composeSyndicateEmbed(syndicateData), file = ayaImage)
                    listOfMessageWithEmbed.append(messageWithEmbed)

                await sleep(max(self.BASE_TIME_TO_WAIT, self.__timeNextVenusSyndicate.timestamp() - time()))

                for messageWithEmberd in listOfMessageWithEmbed:
                    if len(messageWithEmberd.embeds) > 0:
                        messageWithEmberd.embeds[0].color = Color.from_rgb(0xf8, 0, 0)
                        ayaImage = File("resource/alert/aya.png", filename="image.png")
                        # await messageWithEmberd.edit( embed = messageWithEmberd.embeds[0], attachments = [ayaImage, ])
                        await messageWithEmberd.edit( embed = messageWithEmberd.embeds[0], attachments = list())

                return 0

        except: 
            logging.info(traceback.format_exc())

        return self.BASE_TIME_TO_WAIT

    def __composeSyndicateEmbed(self, syndicateData: _SyndicateMissionStruct):

        embed = Embed(
            color = self.AYA_COLOR,
            title = f'{"Цетус" if syndicateData.isCetus else "Долина сфер"}',
            description = f'''{syndicateData.missionName}{" (Сталь)" if syndicateData.isSteel else ""}
Уровни: {syndicateData.minLevel}-{syndicateData.maxLevel}
Конец: <t:{int(self.__timeNextVenusSyndicate.timestamp())}:R>''',
        )
        embed.set_thumbnail(url='attachment://image.png')

        return embed

    def __extractImpotantSyndicatMission(self, listOfSyndicate: list[dict], oldFinishTime: datetime):

        if type(listOfSyndicate) is not list: return None, None

        listOfImpotantMission = list()
        timeFinishArbitraion = None
        syndicateQuantity = 0

        for syndicate in listOfSyndicate:

            if type(syndicate) is dict and syndicate.get('syndicateKey') == 'Ostrons':

                timeFinishArbitraion = self.convertStrToTime(syndicate.get('expiry'))
                if oldFinishTime == timeFinishArbitraion:
                    return None, None
                
                listOfImpotantMission += self.__searchInMissionList(syndicate.get('jobs', []), self.LIST_OF_IMPORTANT_CETUS_SYNDICATE_MISSION, True)
                syndicateQuantity += 1 
                    
            if type(syndicate) is dict and syndicate.get('syndicateKey') == 'Solaris United':

                timeFinishArbitraion = self.convertStrToTime(syndicate.get('expiry'))
                if oldFinishTime == timeFinishArbitraion:
                    return None, None
                
                listOfImpotantMission += self.__searchInMissionList(syndicate.get('jobs', []), self.LIST_OF_IMPORTANT_VENUS_SYNDICATE_MISSION, False)
                syndicateQuantity += 1
            
            if syndicateQuantity == 2:
                return (timeFinishArbitraion, listOfImpotantMission)
        
        return (None, None)
    
    def __searchInMissionList(self, listWithMission: list[dict[any, str]], impotantMission: tuple[str], isCetus):
        missionSelect: list[_SyndicateMissionStruct] = []
        
        for mission in listWithMission:

            if mission.get('type', '').lower() in impotantMission and mission['enemyLevels'][0] in (40, 100):

                missionSelect.append(_SyndicateMissionStruct(mission['type'], mission['enemyLevels'][0] == 100, isCetus, *mission['enemyLevels']))

        return missionSelect

    @commands.command(name = 'setAAC')
    async def setAllAlertChannel(self, ctx: commands.Context, id: int | str = None, *_):
        await self.setAlertChannel(ctx, id, True, True, True)

    @commands.command(name = 'setEIC')
    async def setEidolonChannel(self, ctx: commands.Context, id: int | str = None, *_):
        await self.setAlertChannel(ctx, id, isEidolon = True)

    @commands.command(name = 'setAYAC')
    async def setAyaChannel(self, ctx: commands.Context, id: int | str = None, *_):
        await self.setAlertChannel(ctx, id, isAya = True)

    @commands.command(name = 'setARC')
    async def setArbitrationChannel(self, ctx: commands.Context, id: int | str = None, *_):
        await self.setAlertChannel(ctx, id, isArbitration = True)

    async def setAlertChannel(self, ctx: commands.Context, id: int | str = None, isAya: bool = False, isArbitration: bool = False, isEidolon: bool = False):
        
        if self.__isFobidden(ctx.author.id): return

        if id is None:
            if isAya:
                self.__ayaChannel = None
            if isArbitration:
                self.__arbitrationChannel = None
            if isEidolon:
                self.__eidolonChannel = None
            await ctx.send('Канал удалён')
            self.__updateAlertData()
            return
        
        if type(id) is str and re.match(r'^<#\d{10,20}>$', id):
            id = int(id[2:-1])

        if type(id) is not int:
            await ctx.send('Упс, не вышло')
            return
        
        channel = self.__guild.get_channel(id)

        if channel is None:
            await ctx.send('Упс, не вышло')
            return

        await ctx.send(f'Установлен {channel.mention}')
        if isAya:
            self.__ayaChannel = channel            
            self.__timeNextVenusSyndicate = None
        if isArbitration:
            self.__arbitrationChannel = channel
            self.__timeNextArbitraion = None
        if isEidolon:
            self.__eidolonChannel = channel

        self.__updateAlertData()

    @commands.command(name = 'setEIR')
    async def setEidolonRole(self, ctx: commands.Context, id: int | str = None, *_):
        
        if self.__isFobidden(ctx.author.id): return

        if id is None:
            self.__eidolonRole = None
            await ctx.send('Роль удалёна')
            self.__updateAlertData()
            return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        if type(id) is not int:
            await ctx.send('Упс, не вышло')
            return

        self.__eidolonRole = self.__guild.get_role(id)

        if self.__eidolonRole is None:
            await ctx.send('Упс, не вышло')
            return
        
        await ctx.send(f'Установлен {self.__eidolonRole.mention}')
        self.__updateAlertData()

    @commands.command(name = 'setARR')
    async def setArbitrationRole(self, ctx: commands.Context, id: int | str = None, *_):
        
        if self.__isFobidden(ctx.author.id): return

        if id is None:
            self.__arbitrationRole = None
            await ctx.send('Роль удалёна')
            self.__updateAlertData()
            return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        if type(id) is not int:
            await ctx.send('Упс, не вышло')
            return

        self.__arbitrationRole = self.__guild.get_role(id)

        if self.__arbitrationRole is None:
            await ctx.send('Упс, не вышло')
            return
        
        await ctx.send(f'Установлен {self.__arbitrationRole.mention}')
        self.__updateAlertData()

    @commands.command(name = 'setAYR')
    async def setAyaRole(self, ctx: commands.Context, id: int | str = None, *_):
        
        if self.__isFobidden(ctx.author.id): return

        if id is None:
            self.__ayaRole = None
            await ctx.send('Роль удалёна')
            self.__updateAlertData()
            return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        if type(id) is not int:
            await ctx.send('Упс, не вышло')
            return

        self.__ayaRole = self.__guild.get_role(id)

        if self.__ayaRole is None:
            await ctx.send('Упс, не вышло')
            return
        
        await ctx.send(f'Установлен {self.__ayaRole.mention}')
        self.__updateAlertData()

    def __updateAlertData(self):

        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            data["alerts"] = {
                "eidolon_channel": None if self.__eidolonChannel is None else self.__eidolonChannel.id,
                "arbitration_channel": None if self.__arbitrationChannel is None else self.__arbitrationChannel.id,
                "aya_channel": None if self.__ayaChannel is None else self.__ayaChannel.id,
                "eidolon_role": None if self.__eidolonRole is None else self.__eidolonRole.id,
                "arbitration_role": None if self.__arbitrationRole is None else self.__arbitrationRole.id,
                "aya_role": None if self.__ayaRole is None else self.__ayaRole.id
            }
            
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

    def __isFobidden(self, authorId: int):
        return self.bot.cogs.get('SWDataCog') is None or not (authorId in self.bot.cogs.get('SWDataCog').moderatorsId)
    
    def getHelpMessage(self) -> str:
        return f'''=====Alert Command======
{PREFIX}setEIC <channel/id> - set all channels for alert
{PREFIX}setARC <channel/id> - set channel of eidolon for alert
{PREFIX}setARC <channel/id> - set channel of arbitration for alert
{PREFIX}setAYAC <channel/id> - set channel of aya channel for alert
{PREFIX}setEIR <role/id> - set role of eidolon for alert
{PREFIX}setARR <role/id> - set role of arbitration for alert
{PREFIX}setAYR <role/id> - set role of aya for alert'''
