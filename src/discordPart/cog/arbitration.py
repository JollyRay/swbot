import traceback
from discord.ext import tasks, commands
from discord import Embed, File
import requests
import asyncio
from datetime import datetime, timedelta
import pytz
import json
import re
import logging
from discordPart.cog.patrenCog import SWStandartCog

swBot = None
PREFIX = '♂'

def setup(outerBot: commands.Bot, prefix: str) -> commands.bot:
    global swBot
    global PREFIX

    PREFIX = prefix
    swBot = outerBot

    asyncio.run(swBot.add_cog(ArbitrationCog(swBot)))

class _SyndicateMissionStruct:
    def __init__(self, missionName: str, isSteel: bool, isCetus: bool) -> None:
        self.missionName = missionName
        self.isSteel = isSteel
        self.isCetus = isCetus

class ArbitrationCog(SWStandartCog, name='aritrationCog'):

    LINK_FOR_REQUEST = r'https://api.warframestat.us/pc/arbitration'
    LINK_FOR_SYNDICATE = r'https://api.warframestat.us/pc/syndicateMissions/?language=ru'

    convertStrToTime = staticmethod(lambda stringTime: (datetime.strptime(stringTime, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC)))

    __extractRoleIdFromSting = staticmethod(lambda id: id if re.match(r'^<@&\d{10,20}>$', id) is None else int(id[3:-1]))

    LIST_OF_IMPORTANT_EVENT = (
        'Hydron (Sedna)',
        'Casta (Ceres)',
        'Helene (Saturn)',
        'Odin (Mercury)',
        'Cinxia (Ceres)',
        'Seimeni (Ceres)',
        'Sechura (Pluto)'
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
        
        self.__ayaChannel = None
        self.__ayaChannel = None
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

                if 'arbitration_channel' in data['alerts'].keys():
                    self.__ayaChannel = self.__guild.get_channel(data['alerts']['arbitration_channel'])

                if 'aya_channel' in data['alerts'].keys():
                    self.__ayaChannel = self.__guild.get_channel(data['alerts']['aya_channel'])

                if 'arbitration_role' in data['alerts'].keys():
                    self.__arbitrationRole = self.__guild.get_role(data['alerts']['arbitration_role'])

                if 'aya_role' in data['alerts'].keys():
                    self.__ayaRole = self.__guild.get_role(data['alerts']['aya_role'])

            self.__updateAlertData()

        
        ######################
        #                    #
        #     START LOOP     #
        #                    #
        ######################    
        
        if self.__ayaChannel:
            if self.alertArbitration.is_running():
                self.alertArbitration.restart()
            else:
                self.alertArbitration.start()
        if self.__ayaChannel:
            if self.alertAya.is_running(): 
                self.alertAya.restart()
            else:
                self.alertAya.start()

    @tasks.loop( minutes = 1.0 )
    async def alertArbitration(self):
        try:
        
            if (self.__timeNextArbitraion is None or datetime.now(pytz.UTC).replace(tzinfo=pytz.UTC) > self.__timeNextArbitraion) and self.__ayaChannel:

                respond = requests.get(self.LINK_FOR_REQUEST)

                if respond.status_code != 200: return

                dataDict: dict = respond.json()

                if not ('expiry' in dataDict or 'activation' in dataDict or 'node' in dataDict or 'type' in dataDict):
                    return

                tempTime = self.convertStrToTime(dataDict['expiry'])
                                                 
                if tempTime == self.__timeNextArbitraion: return

                self.__timeNextArbitraion = tempTime
                
                embed = self.__composeArbitrationEmbed(dataDict, tempTime)

                if dataDict["node"] in self.LIST_OF_IMPORTANT_EVENT and self.__arbitrationRole:
                    image = File("resource/alert/arbitration.png", filename="image.png")
                    await self.__ayaChannel.send(embed = embed, file = image)
                

        except: 
            logging.info(traceback.format_exc())

    def __composeArbitrationEmbed(self, dataDict: dict, tempTime: datetime):
        
        tittle: str = dataDict.get('type', '').replace('Dark Sector ', '')

        if tittle.find(dataDict.get('enemy', '♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂♂')) != -1:
            tittle = tittle.replace(dataDict["enemy"], f' - {dataDict["enemy"]}')
        else:
            tittle += f' - {dataDict.get("enemy", "Any")}'

        embed = Embed(
            color = 0xFAEEDD,
            title = tittle,
            description = f'''{self.__arbitrationRole.mention if self.__arbitrationRole else ""} {dataDict.get("node")}
            Ends: <t:{int(tempTime.timestamp())}:R>''',
        )
        embed.set_thumbnail(url='attachment://image.png')

        return embed

    @tasks.loop( minutes = 1.0 )
    async def alertAya(self):
        try:
            if (self.__timeNextVenusSyndicate is None or datetime.now(pytz.UTC).replace(tzinfo=pytz.UTC) > self.__timeNextVenusSyndicate) and self.__ayaChannel:

                respond = requests.get(self.LINK_FOR_SYNDICATE)
                
                if respond.status_code != 200: return
                
                listOfSyndicate: dict = respond.json()

                timeFinishArbitraion, listOfImpotantSyndicateMission = self.__extractImpotantSyndicatMission(listOfSyndicate, self.__timeNextVenusSyndicate)
                
                if timeFinishArbitraion is None: return
                self.__timeNextVenusSyndicate = timeFinishArbitraion
                if listOfImpotantSyndicateMission is None: return
                
                for syndicateData in listOfImpotantSyndicateMission:
                    image = File("resource/alert/aya.png", filename="image.png")
                    await self.__ayaChannel.send( embed = self.__composeSyndicateEmbed(syndicateData), file = image)

        except: 
            logging.info(traceback.format_exc())

    def __composeSyndicateEmbed(self, syndicateData: _SyndicateMissionStruct):

        embed = Embed(
            color = 0xFAEEDD,
            title = f'{"Цетус" if syndicateData.isCetus else "Долина сфер"}',
            description = f'''{syndicateData.missionName}{" (Сталь)" if syndicateData.isSteel else ""}
            Ends: <t:{int(self.__timeNextVenusSyndicate.timestamp())}:R>''',
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

            if type(mission) and mission.get('type', '').lower() in impotantMission and mission['enemyLevels'][0] in (40, 100):

                missionSelect.append(_SyndicateMissionStruct(mission['type'], mission['enemyLevels'][0] == 100, isCetus))

        return missionSelect

    @commands.command(name = 'setAAC')
    async def setAllAlertChannel(self, ctx: commands.Context, id: int | str = None, *_):
        await self.setAlertChannel(ctx, id, True, True)

    @commands.command(name = 'setAYAC')
    async def setAyaChannel(self, ctx: commands.Context, id: int | str = None, *_):
        await self.setAlertChannel(ctx, id, True, False)

    @commands.command(name = 'setARC')
    async def setArbitrationChannel(self, ctx: commands.Context, id: int | str = None, *_):
        await self.setAlertChannel(ctx, id, False, True)

    async def setAlertChannel(self, ctx: commands.Context, id: int | str = None, isAya: bool = False, isArbitration: bool = False):
        
        if self.__isFobidden(ctx.author.id): return

        if id is None:
            if isAya:
                self.__ayaChannel = None
                self.alertAya.stop()
            if isArbitration:
                self.__ayaChannel = None
                self.alertArbitration.stop()
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
            if self.alertAya.is_running():
                self.alertAya.restart()
            else:
                self.alertAya.start()
        if isArbitration:
            self.__ayaChannel = channel
            self.__timeNextArbitraion = None
            if self.alertArbitration.is_running():
                self.alertArbitration.restart()
            else:
                self.alertArbitration.start()

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
                "arbitration_channel": None if self.__ayaChannel is None else self.__ayaChannel.id,
                "aya_channel": None if self.__ayaChannel is None else self.__ayaChannel.id,
                "arbitration_role": None if self.__arbitrationRole is None else self.__arbitrationRole.id,
                "aya_role": None if self.__ayaRole is None else self.__ayaRole.id
            }
            
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

    def __isFobidden(self, authorId: int):
        return self.bot.cogs.get('SWDataCog') is None or not (authorId in self.bot.cogs.get('SWDataCog').moderatorsId)
    
