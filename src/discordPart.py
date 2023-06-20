import functools
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from enum import Enum, auto
import json
import logging
import re

# Утанавливать каналы для чтения
# Устанавливать каналы для оповещений
# Set clan role id
# Set moderator
# Измерение профиля
# Определение вклада
# Save logs

PREFIX = '♂'
swBot = None

def setupDiscordBot() -> commands.bot:
    global swBot

    if swBot is None:
        intents = discord.Intents.all()
        swBot = commands.Bot(command_prefix = PREFIX, intents = intents)

        swBot.remove_command('help')
        
        @swBot.check
        async def globallyBlockAnonymousUser(ctx):
            if ctx.author is None:
                logging.info('None:None:message from non-user')
                return False
            return True

        for cog in ALL_COGS:
            asyncio.run(swBot.add_cog(cog(swBot)))

    return swBot

#################################
#                               #
#             UTIL              #
#                               #
#################################

class CommandStuct:
    STANDART_SUCCESSFULL_MESSAGE = 'Success'
    STANDART_FAILED_MESSAGE = 'Failed'

    def __init__(self, name: str = '???', createDescription: str | None = None, createSuccessfulExecutionMessage: str | None = None, createFailedExecutionMessage: str | None = None) -> None:
        self._commandName = name
        self._createDescription = createDescription
        self._createSuccessfulExecutionMessage = createSuccessfulExecutionMessage
        self._createFailedExecutionMessage = createFailedExecutionMessage

    @property
    def commandName(self) -> str:
        return self._commandName

    def getDescription(self, prefix: str = PREFIX, *args) -> str:

        if self._createDescription is None:
            return None
        
        if type(self._createDescription) is str:
            return self._createDescription

        return self._createDescription(prefix, self.commandName, *args)
    
    def getSuccessAnswer(self, *args) -> str:

        if self._createSuccessfulExecutionMessage is None:
            return self.STANDART_SUCCESSFULL_MESSAGE
        
        if type(self._createSuccessfulExecutionMessage) is str:
            return self._createSuccessfulExecutionMessage
        
        return self._createSuccessfulExecutionMessage(*args)
      
    def getFailedAnswer(self, *args) -> str:

        if self._createFailedExecutionMessage is None:
            return self.STANDART_FAILED_MESSAGE
        
        if type(self._createFailedExecutionMessage) is str:
            return self._createFailedExecutionMessage
        
        return self._createFailedExecutionMessage(*args)

class CommandProperty:
    SetterCFP: CommandStuct = CommandStuct(
        name = 'setCFP',
        createDescription = lambda prefix: '%ssetCFP <id> - set channel for parse profile & set clan role' % (prefix),
        createSuccessfulExecutionMessage = lambda name, id: 'Channel for profile parse is removed' if id is None else 'Channel "%s"(%s) is selected for profile parse' % (name, id),
        createFailedExecutionMessage = lambda _ = None, id = None: 'Channel (%s) is not found' % id
    )
    SetterCFR: CommandStuct = CommandStuct(
        name = 'setCFR',
        createDescription = lambda prefix: '%ssetCFR <id> - set channel for parse profile on resource' % (prefix),
        createSuccessfulExecutionMessage = lambda name, id: 'Channel for resource parse is removed' if id is None else 'Channel "%s"(%s) is selected for resource parse' % (name, id),
        createFailedExecutionMessage = lambda _ = None, id = None: 'Channel (%s) is not found' % id
    )
    SetterCFA: CommandStuct = CommandStuct(
        name = 'setCFA',
        createDescription = lambda prefix: '%ssetCFA <clan name> <id> - set channel for alert' % (prefix),
        createSuccessfulExecutionMessage = lambda channelName, channelId = None: 'Alert (for %s) wont send' % channelName if channelId is None else 'Alert will send to channel %s (%s)' % (channelName, channelId),
        createFailedExecutionMessage = lambda channelName = None, id = None: 'Clan not found' % channelName if id is None else 'Channel (%s) is not found' % id
    )
    SetterCRI: CommandStuct = CommandStuct(
        name = 'setCRI',
        createDescription = lambda prefix: '%ssetCRI <clan name> <id> - set role for clan' % (prefix),
        createSuccessfulExecutionMessage = lambda clanName, roleId: 'Remove role for %s' % clanName if roleId is None else 'Connect role %s with clan %s' % (roleId, clanName),
        createFailedExecutionMessage = lambda clanName, _ = None: 'Clan not found' if clanName is None else 'Cant connect clan with role'
    )
    AdderC: CommandStuct = CommandStuct(
        name = 'addC',
        createDescription = lambda prefix: '%saddC <clan name> - add clan' % (prefix),
        createSuccessfulExecutionMessage = lambda clanName, _ = None: 'Add new clan "%s' % (clanName),
        createFailedExecutionMessage = lambda clanName = None, _ = None: 'Title not specified' if clanName is None else '%s exists' % (clanName)
    )
    DeleterC: CommandStuct = CommandStuct(
        name = 'delC',
        createDescription = lambda prefix: '%sdelC <clan name> - delete clan' % (prefix),
        createSuccessfulExecutionMessage = lambda clanName, _ = None: 'Clan (%s) is deleted' % (clanName),
        createFailedExecutionMessage = lambda clanName, _ = None: 'Clan name is none' if clanName is None else 'Clan (%s) is not found' % (clanName),
    )
    AdderModerator: CommandStuct = CommandStuct(
        name = 'addM',
        createDescription = lambda prefix: '%saddM <user id> - add moderator to list' % (prefix),
        createSuccessfulExecutionMessage = lambda _ = None, userId = None: 'Moderator (%s) is added to moder list' % (userId),
        createFailedExecutionMessage = lambda _ = None, userId = None: 'Id is not id format' if userId is None else '%s exists' % (userId)
    )
    DeleterModerator: CommandStuct = CommandStuct(
        name = 'delM',
        createDescription = lambda prefix: '%sdelM <user id> - delete moderator from list' % (prefix),
        createSuccessfulExecutionMessage = lambda _ = None, userId = None: 'Moderator (%s) is deleted from moder list' % (userId),
        createFailedExecutionMessage = lambda userId:'Id is not id format' if userId is None else '%s not exist'
    )
    ShowStage: CommandStuct = CommandStuct(
        name = 'show',
        createDescription = lambda prefix: '%sshow - show all info' % (prefix)
    )
    Help: CommandStuct = CommandStuct(
        name = 'help'
    )

#################################
#                               #
#           Discord             #
#                               #
#################################

class SWCog(commands.Cog):

    def __init__(self, clinet: commands.Bot) -> None:
        self.bot: commands.Bot = clinet
        
        self.__superMod = False
        self.__superModers = [275357556862484484]
        
    @commands.Cog.listener()
    async def on_ready(self):
        
        with open('resource/data.json', encoding='utf8') as dataFile:
            data: dict[str, any] = json.load( dataFile )

            if 'guild_id' in data.keys():
                self.__guild = self.bot.get_guild(data['guild_id'])

                @self.bot.check
                async def globallyBlockPM(ctx):
                    if ctx.guild is None or ctx.guild.id != self.__guild.id:
                        logging.info(f'{ctx.author}:None:message from PM')
                        return False
                    return True

            else:
                raise NameError('Guild is not set')

            self.__clanLinks: dict[str, dict[str, int | None]] = {}
            try:
                if 'all_clans_name' in data.keys():
                    self.__clanLinks: dict[str, dict[str, int | None]] = data['all_clans_name']

                    for clanName, clanLink in data['all_clans_name'].items():

                        self.__clanLinks[clanName] = {
                            'role': None if clanLink['role'] is None else self.__guild.get_role(clanLink['role']),
                            'alert_channel': None if clanLink['alert_channel'] is None else self.__guild.get_channel(clanLink['alert_channel'])
                        }
                else:
                    logging.warning(':WARING! Missing key "all_clans_name"')
            except:
                logging.warning(':WARING! Missing keys in "all_clans_name"')

            if 'all_moderator' in data.keys():
                self.__allModers: list[int] = data['all_moderator']
            else:
                logging.warning(':WARING! Missing key "all_moderator"')
                self.__allModers: list[int] = []
                
            self.__profileChannel: discord.TextChannel | None = None if data.get('profile_channel', None) is None else self.__guild.get_channel(data['profile_channel'])
            if self.__profileChannel is None:
                logging.warning(':WARING! Undefind "profile_channel"')

            self.__resourceChannel: discord.TextChannel | None = None if data.get('resource_channel', None) is None else self.__guild.get_channel(data['resource_channel'])
            if self.__resourceChannel is None:
                logging.warning(':WARING! Undefind "resource_channel"')

        self.__updateAllData()

        print('#' * 44, '', f'\tLogged on as {self.bot.user}!', '', '#' * 44, sep = '\n')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.content.startswith(PREFIX):
        #     await self.bot.process_commands(message)
            return

        if self.__superMod:
            if not message.author.id in self.__superModers:
                return

        if message.author == self.bot.user:
            return
        
        print(f'Message from {message.author}: {message.content}')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        
        if type(error) is commands.CommandNotFound:
            logging.warning(f'{ctx.author.name}:{error}')

    @commands.command(name = CommandProperty.SetterCFP.commandName)
    async def setChannelForProfileParser(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if type(id) is str:
            id = self.__extractChannelIdFromString(id)
        isPossible, message = self.__isPossibilities(ctx, None, id, CommandProperty.SetterCFP, self.__guild.text_channels)

        if isPossible:
        
            self.__profileChannel = self.__guild.get_channel(id)
            self.__updateProfileParserData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = CommandProperty.SetterCFR.commandName)
    async def setChannelForProfileResource(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if type(id) is str:
            id = self.__extractChannelIdFromString(id)
        isPossible, message = self.__isPossibilities(ctx, None, id, CommandProperty.SetterCFR, self.__guild.text_channels)

        if isPossible:
            
            self.__resourceChannel = self.__guild.get_channel(id)
            self.__updateResourceParserData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = CommandProperty.SetterCFA.commandName)
    async def setChannelForAlert(self, ctx: commands.Context, clanName: str, id: int | str = None, *, member: discord.Member = None):

        if not (clanName in self.__clanLinks.keys()) :
            logging.info(f'{CommandProperty.SetterCFA.commandName}:clan not found:{clanName}:{id}')
            await ctx.send(CommandProperty.SetterCFA.getFailedAnswer(clanName, id))
            return

        if type(id) is str:
            id = self.__extractChannelIdFromString(id)
        isPossible, message = self.__isPossibilities(ctx, clanName, id, CommandProperty.SetterCFA, self.__guild.text_channels)

        if isPossible:

            self.__clanLinks[clanName]['alert_channel'] = self.__guild.get_channel(id)
            self.__updateClanData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = CommandProperty.SetterCRI.commandName)
    async def setClanRoleId(self, ctx: commands.Context, clanName: str, id: int | str = None, *, member: discord.Member = None):

        if not (clanName in self.__clanLinks.keys()):
            logging.info(f'{CommandProperty.SetterCRI.commandName}:clan not found:{clanName}:{id}')
            await ctx.send(CommandProperty.SetterCRI.getFailedAnswer(None))
            return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        isPossible, message = self.__isPossibilities(ctx, clanName, id, CommandProperty.SetterCRI, self.__guild.roles)

        if isPossible:
            
            self.__clanLinks[clanName]['role'] = self.__guild.get_role(id)
            self.__updateClanData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = CommandProperty.AdderC.commandName)
    async def addClan(self, ctx: commands.Context, clanName: str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.AdderC): return

        if clanName is None:
            logging.info(f'{CommandProperty.AdderC.commandName}:clan is none:{clanName}')
            ctx.send(CommandProperty.AdderC.getFailedAnswer())
            return

        if clanName.lower() in [clan.lower() for clan in self.__clanLinks.keys()]:
            logging.info(f'{CommandProperty.AdderC.commandName}:clan exists:{clanName}')
            await ctx.send(CommandProperty.AdderC.getFailedAnswer(clanName))
            return
        
        self.__clanLinks[clanName] = {'role': None, 'alert_channel': None}
        self.__updateClanData()

        logging.info(f'{CommandProperty.AdderC.commandName}:clan add:{clanName}')
        await ctx.send(CommandProperty.AdderC.getSuccessAnswer(clanName))

    @commands.command(name = CommandProperty.DeleterC.commandName)
    async def deleteClan(self, ctx: commands.Context, clanName: str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.DeleterC): return

        if clanName is None:
            logging.info(f'{CommandProperty.DeleterC.commandName}:clan is none:{clanName}')
            await ctx.send(CommandProperty.DeleterC.getFailedAnswer())
            return

        if not (clanName.lower() in [clan.lower() for clan in self.__clanLinks.keys()]):
            logging.info(f'{CommandProperty.DeleterC.commandName}:clan not exist:{clanName}')
            await ctx.send(CommandProperty.DeleterC.getFailedAnswer(clanName))
            return
        
        del self.__clanLinks[clanName]
        self.__updateClanData()

        logging.info(f'{CommandProperty.DeleterC.commandName}:clan delete:{clanName}')
        await ctx.send(CommandProperty.DeleterC.getSuccessAnswer(clanName))

    @commands.command(name = CommandProperty.AdderModerator.commandName)
    async def addModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.AdderModerator): return

        if type(id) is str:
            id = self.__extractMemberIdFromString(id)

        if type(id) is not int:
            logging.info(f'{CommandProperty.AdderModerator.commandName}:id is none::{id}')
            await ctx.send(CommandProperty.AdderModerator.getFailedAnswer())
            return

        if id in self.__allModers:
            logging.info(f'{CommandProperty.AdderModerator.commandName}:moderator exists::{id}')
            await ctx.send(CommandProperty.AdderModerator.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__allModers.append(id)
            data["all_moderator"] = self.__allModers
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{CommandProperty.AdderModerator.commandName}:moderator add::{id}')
        await ctx.send(CommandProperty.AdderModerator.getSuccessAnswer(None, id))

    @commands.command(name = CommandProperty.DeleterModerator.commandName)
    async def deleteModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.DeleterModerator): return

        if type(id) is str:
            id = self.__extractMemberIdFromString(id)

        if id is None:
            logging.info(f'{CommandProperty.DeleterModerator.commandName}:id is none:{id}')
            await ctx.send(CommandProperty.DeleterModerator.getFailedAnswer())
            return

        if not ( id in self.__allModers ):
            logging.info(f'{CommandProperty.DeleterModerator.commandName}:moderator not exist::{id}')
            await ctx.send(CommandProperty.DeleterModerator.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__allModers.remove(id)
            data["all_moderator"] = self.__allModers
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{CommandProperty.DeleterModerator.commandName}:moderator delete:{id}')
        await ctx.send(CommandProperty.DeleterModerator.getSuccessAnswer(None, id))

    @commands.command(name = CommandProperty.ShowStage.commandName)
    async def showStage(self, ctx: commands.Context, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.ShowStage): return

        info: str = '======Info======\n'

        info += f'Profile parse from {None if self.__profileChannel is None else self.__profileChannel.mention}\n'

        info += f'Resource parse from {None if self.__resourceChannel is None else self.__resourceChannel.mention}\n'

        info += 'Moders: '
        for id in self.__allModers:
            
            member = self.__guild.get_member(id)

            if not (member is None):
                info += f'{member.mention} '

        info += '\n\n'

        for clanName, links in self.__clanLinks.items():

            info += f'{clanName} '

            if links['role'] is None:
                info += '() -> '
            else:
                info += f'({links["role"].mention}) -> '

            if not (links['alert_channel'] is None):
                info += f'{links["alert_channel"].mention}'

            info += '\n'

        await ctx.send(info)
        return

    @commands.command(name = CommandProperty.Help.commandName)
    async def helpSWCommand(self, ctx: commands.Context, *args, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.Help): return
        
        print(args)

    def __updateAllData(self):
        self.__updateClanData()
        self.__updateProfileParserData()
        self.__updateResourceParserData()

    def __updateClanData(self):
        newData = {}

        for clanName, clanLinks in self.__clanLinks.items():
            
            newData[clanName] = {
                'role': None if clanLinks['role'] is None else clanLinks['role'].id,
                'alert_channel': None if clanLinks['alert_channel'] is None else clanLinks['alert_channel'].id
            }

        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            data["all_clans_name"] = newData
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

    def __updateProfileParserData(self):
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            data["profile_channel"] = None if self.__profileChannel is None else self.__profileChannel.id
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

    def __updateResourceParserData(self):
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            data["resource_channel"] = None if self.__resourceChannel is None else self.__resourceChannel.id
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

    def __verifyAccess(self, ctx: commands.Context, targetCommandObject: CommandStuct) -> bool:
        if ctx.author.id in self.__allModers or ctx.author.id in self.__superMod:
            return True
        logging.info(f'{ctx.author.name}:{targetCommandObject.commandName}:message from common user')
        return False

    def __isPossibilities(self, ctx: commands.Context, name: str | None, id: int | None, targetCommandObject: CommandStuct, listForSearch: list) -> bool:
        
        if not self.__verifyAccess(ctx, targetCommandObject):
            return (False, None)

        if id is None:

            logging.info(f'{ctx.author.name}:{targetCommandObject.commandName}:success:{name}:None')
            return (True, targetCommandObject.getSuccessAnswer(name, None))

        if not type(id) is int:

            logging.info(f'{ctx.author.name}:{targetCommandObject.commandName}:uncorrect id:{name}:{id}')
            return (False, None)
        
        iter = discord.utils.find(lambda iter: iter.id == id, listForSearch)

        if iter is not None:
            logging.info(f'{ctx.author.name}:{targetCommandObject.commandName}:success:{name}:{id}')

            return (True, targetCommandObject.getSuccessAnswer(iter.name, iter.id))
            
        logging.info(f'{ctx.author.name}:{targetCommandObject.commandName}:uncorrect id:{name}:{id}')

        return (False, targetCommandObject.getFailedAnswer(name, id))

    __extractRoleIdFromSting = staticmethod(lambda id: id if re.match(r'^<@&\d{10,20}>$', id) is None else int(id[3:-1]))
    __extractChannelIdFromString = staticmethod(lambda id: id if re.match(r'^<#\d{10,20}>$', id) is None else int(id[2:-1]))
    __extractMemberIdFromString = staticmethod(lambda id: id if re.match(r'^<@\d{10,20}>$', id) is None else int(id[2:-1]))

    @commands.command(name = 'flip')
    async def flipMod(self, ctx: commands.Context, *, member: discord.Member = None):
        if ctx.author.id in self.__superModers:
            self.__superMod = not self.__superMod

            await ctx.send('Set super mod' if self.__superMod else 'Set noraml mod')

    
ALL_COGS = [SWCog]