import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import logging
import re
from io import BytesIO
from PIL import Image
from profileParser import MainProfileParser, ResourceProfileParser, wordSimplificationEng
from Levenshtein import ratio
from asyncio import sleep 
from collections.abc import Iterable

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

# Sec
TIMEOUT_BEFORE_DELETE = 180

class MessageForAnswers:
    HEADER_FOR_PROFILE_BRANCH = 'Уточнение ника'
    QUESTION_ABOUT_POTANTIAL_NAME = 'Вы не указали имя перед скринштом. С него было считано "{}" это ваше имя?'
    IF_PARSE_AND_NICK_DIFFERENT = 'Пожалуйста, напишите свой ник без суффикса после #, тега клана и иных добавлений **В ЭТУ ВЕТКУ**. Если ваш ник содержит форматирующие вставки (как например _), то вы можете экранировать свой ник с помощью `, но это не обязательно.'
    ANSWER_FOR_FAILED_PARSE_PROFILE = '{} из-за технических шоколадок что-то пошло не так, пожалуйста дождитесь модератора. Он вручную выдаст вам роль.'
    IF_RESOURCE_PARSER_BREAK = 'Пожалуйста, дождитесь администрации вашего клана. Оповещение им отправлено.'

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
    def __new__(cls,*args):
        if cls is CommandProperty:
            return None
        return object.__new__(cls,*args)
    
    SetterCFPI: CommandStuct = CommandStuct(
        name = 'setCFPI',
        createDescription = lambda prefix: '%ssetCFPI <id> - set channel for info about error in profile parser channel' % (prefix),
        createSuccessfulExecutionMessage = lambda name, id: 'Channel for profile parse is removed' if id is None else 'Channel "%s"(%s) is selected for profile parse' % (name, id),
        createFailedExecutionMessage = lambda _ = None, id = None: 'Channel (%s) is not found' % id
    )
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
    AdderSR: CommandStuct = CommandStuct(
        name = 'addSR',
        createDescription = lambda prefix: '%saddSR <role id> - add start role' % (prefix),
        createSuccessfulExecutionMessage = lambda roleName = None, _ = None: 'Add role (%s)' % (roleName),
        createFailedExecutionMessage = lambda _ = None, userId = None: 'Id is not id format' if userId is None else '%s exists' % (userId)
    )
    DeleterSR: CommandStuct = CommandStuct(
        name = 'delSR',
        createDescription = lambda prefix: '%sdelSR <role id> - delete start role' % (prefix),
        createSuccessfulExecutionMessage = lambda roleName = None, _ = None: 'Delete role (%s)' % (roleName),
        createFailedExecutionMessage = lambda _ = None, userId = None: 'Id is not id format' if userId is None else '%s exists' % (userId)
    )
    ShowStage: CommandStuct = CommandStuct(
        name = 'show',
        createDescription = lambda prefix: '%sshow - show all info' % (prefix)
    )
    Help: CommandStuct = CommandStuct(
        name = 'help'
    )

class TempThread:

    def __init__(self, name: str, role: discord.Role, currentMessage: discord.Message, thread: discord.Thread, view) -> None:
        
        self.name = name
        self.role = role
        self.currentMessage = currentMessage
        self.thread = thread
        self.view = view

class InfoForReport:

    def __init__(self, currentMessage: discord.Message, rank: int) -> None:
        self.__currentMessage = currentMessage
        self.__rank = rank

    def getText(self) -> str:
        return f'1. {self.__currentMessage.author} {self.__currentMessage.author.mention}\n2. Magiaicn (2-ой способ)\n3. {self.__rank} ранг'
    
    def getFiles(self) -> list[discord.File]:
        return [a.to_file() for a in self.__currentMessage.attachments]

async def setClanRoleForMember(member: discord.Member, role: discord.Role):

    for clanLinks in swBot.cogs['SWCog'].clanLinks.values():

        if clanLinks['role'] in member.roles:

            await member.remove_roles(clanLinks['role'])

    for startRole in swBot.cogs['SWCog'].startRole:

        if startRole in member.roles:

            await member.remove_roles(startRole)

    await member.add_roles(role)

async def finishWithMember(author: discord.Member = None, name: str = None, role: discord.Role = None, currentMessage: Iterable[discord.Message] | discord.Message = None, thread: Iterable[discord.Thread] | discord.Thread = None):
    if all((author, role)):
        try:
            await setClanRoleForMember(author, role)
        except Exception: pass

    if all((author, name)):
        try:
            await author.edit( nick = name)
        except Exception: pass

    if currentMessage is not None:
        try:
            if isinstance(currentMessage, Iterable):
                for message in currentMessage:
                    await message.delete()
            else:
                await currentMessage.delete()
        except Exception: pass


    if thread is not None:
        try:
            if isinstance(thread, Iterable):
                for message in thread:
                    await message.delete()
            else:
                await thread.delete()
        except Exception: pass

def attemptExtractRank(comment: str) -> int:

    if len(comment) > 4:

        isLegendary = comment.find('лег') >= 0

        allNumbersInComment = re.findall( r'[^-._a-zA-Z0-9]\d{1,2}[ -]', comment )

        if len(allNumbersInComment) == 1:
            return int(allNumbersInComment[0][1:-1]) + 30 * isLegendary
        
        if len(allNumbersInComment) > 1:
            
            for i in range(6):
                if int(allNumbersInComment[i][1:-1]) != i:
                    return int(allNumbersInComment[i][1:-1]) + 30 * isLegendary

    return None

#################################
#                               #
#           Discord             #
#                               #
#################################

class ResourceQuestionnaireView(discord.ui.View):

    def __init__(self, *, currentMessage: discord.Message, thread: discord.Thread, moderChannelForHelp: discord.TextChannel):
        super().__init__(timeout = TIMEOUT_BEFORE_DELETE)

        self.__currentMessage = currentMessage
        self.__messageWithButton: discord.Message = None
        self.__thread = thread
        self.__moderChannelForHelp = moderChannelForHelp

    async def on_timeout(self):
        await finishWithMember(currentMessage=self.__messageWithButton)

    async def disableAllButton(self):

        for item in self.children:

            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.__messageWithButton is None:
            await sleep(1)

        await self.__messageWithButton.edit(view = self)

    @discord.ui.button( label = 'Подтверждаю', style = discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.Button):
        
        if self.__currentMessage.author.id is interaction.user.id:
            await finishWithMember(currentMessage = self.__currentMessage, thread = self.__thread)

        await interaction.response.defer()

    @discord.ui.button( label = 'Система ошиблась', style = discord.ButtonStyle.red)
    async def refuse(self, interaction: discord.Interaction, button: discord.Button):

        if self.__currentMessage.author.id is interaction.user.id:
            await self.disableAllButton()
            await interaction.response.send_message(MessageForAnswers.IF_RESOURCE_PARSER_BREAK)
            await self.__moderChannelForHelp.send(f'{self.__currentMessage.author.mention} утверждает о верности своего вклада')
        else:
            await interaction.response.defer()


    @property
    def messageWithButton(self):
        return self.__messageWithButton
    
    @messageWithButton.setter
    def messageWithButton(self, newMessage):
        self.__messageWithButton = newMessage


class NameQuestionnaireView(discord.ui.View):

    def __init__(self, *, name: str, role: discord.Role, currentMessage: discord.Message, thread: discord.Thread):
        super().__init__(timeout = TIMEOUT_BEFORE_DELETE)

        self.__name = name
        self.__role = role
        self.__currentMessage = currentMessage
        self.__messageWithButton: discord.Message = None
        self.__thread = thread
        self.__isDone = False
        self.__needWaitForModerator = False

    async def on_timeout(self):
        if not self.__needWaitForModerator:
            await finishWithMember(currentMessage=self.__currentMessage, thread = self.__thread)
        swBot.cogs['SWCog'].removeAdditionalThread(self.__thread.id)

    async def disableAllButton(self):

        for item in self.children:

            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.__messageWithButton is None:
            await sleep(1)

        await self.__messageWithButton.edit(view = self)

    @discord.ui.button( label = 'Подтверждаю', style = discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.Button):
        
        if self.__currentMessage.author.id is interaction.user.id and not self.__isDone:
            self.__isDone = True
            await interaction.response.defer()
            await self.disableAllButton()
            await finishWithMember(self.__currentMessage.author, self.__name, self.__role, self.__currentMessage, self.__thread)
        else:
            await interaction.response.defer()

    @discord.ui.button( label = 'Отклоняю', style = discord.ButtonStyle.red)
    async def refuse(self, interaction: discord.Interaction, button: discord.Button):

        if self.__currentMessage.author.id is interaction.user.id and not self.__isDone:
            self.__isDone = True
            await self.disableAllButton()
            swBot.cogs['SWCog'].addAdditionalThread(TempThread(self.__name, self.__role, self.__currentMessage, self.__thread, self))
            await interaction.response.send_message(MessageForAnswers.IF_PARSE_AND_NICK_DIFFERENT)
        else:
            await interaction.response.defer()
        
    def setNamesTooDifferent(self):
        self.__needWaitForModerator = True

    @property
    def messageWithButton(self):
        return self.__messageWithButton
    
    @messageWithButton.setter
    def messageWithButton(self, newMessage):
        self.__messageWithButton = newMessage

class SWCog(commands.Cog, name='SWCog'):

    MAX_BUFFER_SIZE = 3e7
    MINIMUM_PART_MATHC = 0.75
    RESOURCE_QUANTITY_TYPE = 2

    def __init__(self, clinet: commands.Bot) -> None:
        self.bot: commands.Bot = clinet
        
        self.__superMod = False
        self.__superModers = [275357556862484484]

        self.__additionalThread: dict[int: TempThread] = {}
        self.__reportLink: dict[int, tuple] = {}
        
    @commands.Cog.listener()
    async def on_ready(self):
        
        with open('resource/data.json', encoding='utf8') as dataFile:
            data: dict[str, any] = json.load( dataFile )

            if 'guild_id' in data.keys():
                self.__guild = self.bot.get_guild(data['guild_id'])

                @self.bot.check
                async def globallyBlockPM(ctx):

                    if ctx.guild is None:
                        logging.info(f'{ctx.author}:None:message from PM')
                        return False
                    
                    if ctx.guild.id != self.__guild.id:
                        logging.info(f'{ctx.author}/{ctx.guild.id}:None:message from other guild')
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
                    logging.warning('::WARING! Missing key "all_clans_name"')
            except Exception:
                logging.warning('::WARING! Missing keys in "all_clans_name"')

            if 'all_moderator' in data.keys():
                self.__allModers: list[int] = data['all_moderator']
            else:
                logging.warning('::WARING! Missing key "all_moderator"')
                self.__allModers: list[int] = []
                
            if 'start_roles' in data.keys():
                self.__startRoles: list[discord.Role] = [self.__guild.get_role(roleId) for roleId in data['start_roles']]
            else:
                logging.warning('::WARING! Missing key "start_roles"')
                self.__startRoles: list[discord.Role] = []
                
            if 'profile_info_channel' in data.keys():
                self.__profileParseInfoChannel: discord.TextChannel = self.__guild.get_channel(data['profile_info_channel'])
            else:
                logging.warning('::WARING! Missing key "profile_info_channel"')
                self.__profileParseInfoChannel: discord.TextChannel = None
                
            self.__profileChannel: discord.TextChannel | None = None if data.get('profile_channel', None) is None else self.__guild.get_channel(data['profile_channel'])
            if self.__profileChannel is None:
                logging.warning('::WARING! Undefind "profile_channel"')

            self.__resourceChannel: discord.TextChannel | None = None if data.get('resource_channel', None) is None else self.__guild.get_channel(data['resource_channel'])
            if self.__resourceChannel is None:
                logging.warning('::WARING! Undefind "resource_channel"')

        self.__updateAllData()

        print('#' * 44, '', f'\tLogged on as {self.bot.user}!', '', '#' * 44, sep = '\n')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.content.startswith(PREFIX):
        #     await self.bot.process_commands(message)
            return

        if message.author == self.bot.user:
            return

        if self.__profileChannel is message.channel:
            
            isSuccess = await self.__profileHandler(message)

            if not isSuccess:
                await message.channel.send( MessageForAnswers.ANSWER_FOR_FAILED_PARSE_PROFILE.format(message.author.mention), delete_after = TIMEOUT_BEFORE_DELETE )
                
                if self.__profileParseInfoChannel is not None:
                    try:
                        await self.__profileParseInfoChannel.send(f'Не вышло обработать {message.author.mention}')
                    except Exception: pass
            return

        if self.__resourceChannel is message.channel:
            
            await self.__resourceHandler(message)
            return
        
        if message.channel.id in self.__additionalThread:
            
            isSuccess = await self.__additionalThreadHandler(message, self.__additionalThread.get(message.channel.id, None))

            if not isSuccess:
                await message.channel.send(MessageForAnswers.ANSWER_FOR_FAILED_PARSE_PROFILE.format(message.author.mention))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        
        if type(error) is commands.CommandNotFound:
            logging.warning(f'{ctx.author.name}::{error}')

    @commands.command(name = CommandProperty.SetterCFPI.commandName)
    async def setChannelForProfileParserInfo(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):

        if type(id) is str:
            id = self.__extractChannelIdFromString(id)

        isPossible, message = self.__isPossibilities(ctx, None, id, CommandProperty.SetterCFPI, self.__guild.text_channels)

        if isPossible:
        
            self.__profileParseInfoChannel = self.__guild.get_channel(id)
            self.__updateProfileParserInfoData()

        if not (message is None):
            await ctx.send(message)

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
            logging.info(f'{ctx.author}:{CommandProperty.SetterCFA.commandName}:clan not found:{clanName}:{id}')
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
            logging.info(f'{ctx.author}:{CommandProperty.SetterCRI.commandName}:clan not found:{clanName}:{id}')
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
            logging.info(f'{ctx.author}:{CommandProperty.AdderC.commandName}:clan is none:{clanName}')
            ctx.send(CommandProperty.AdderC.getFailedAnswer())
            return

        if clanName.lower() in [clan.lower() for clan in self.__clanLinks.keys()]:
            logging.info(f'{ctx.author}:{CommandProperty.AdderC.commandName}:clan exists:{clanName}')
            await ctx.send(CommandProperty.AdderC.getFailedAnswer(clanName))
            return
        
        self.__clanLinks[clanName] = {'role': None, 'alert_channel': None}
        self.__updateClanData()

        logging.info(f'{ctx.author}:{CommandProperty.AdderC.commandName}:clan add:{clanName}')
        await ctx.send(CommandProperty.AdderC.getSuccessAnswer(clanName))

    @commands.command(name = CommandProperty.DeleterC.commandName)
    async def deleteClan(self, ctx: commands.Context, clanName: str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.DeleterC): return

        if clanName is None:
            logging.info(f'{ctx.author}:{CommandProperty.DeleterC.commandName}:clan is none:{clanName}')
            await ctx.send(CommandProperty.DeleterC.getFailedAnswer())
            return

        if not (clanName.lower() in [clan.lower() for clan in self.__clanLinks.keys()]):
            logging.info(f'{ctx.author}:{CommandProperty.DeleterC.commandName}:clan not exist:{clanName}')
            await ctx.send(CommandProperty.DeleterC.getFailedAnswer(clanName))
            return
        
        del self.__clanLinks[clanName]
        self.__updateClanData()

        logging.info(f'{ctx.author}:{CommandProperty.DeleterC.commandName}:clan delete:{clanName}')
        await ctx.send(CommandProperty.DeleterC.getSuccessAnswer(clanName))

    @commands.command(name = CommandProperty.AdderModerator.commandName)
    async def addModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.AdderModerator): return

        if type(id) is str:
            id = self.__extractMemberIdFromString(id)

        if type(id) is not int:
            logging.info(f'{ctx.author}:{CommandProperty.AdderModerator.commandName}:id is none::{id}')
            await ctx.send(CommandProperty.AdderModerator.getFailedAnswer())
            return

        if id in self.__allModers:
            logging.info(f'{ctx.author}:{CommandProperty.AdderModerator.commandName}:moderator exists::{id}')
            await ctx.send(CommandProperty.AdderModerator.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__allModers.append(id)
            data["all_moderator"] = self.__allModers
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{ctx.author}:{CommandProperty.AdderModerator.commandName}:moderator add::{id}')
        await ctx.send(CommandProperty.AdderModerator.getSuccessAnswer(None, id))

    @commands.command(name = CommandProperty.DeleterModerator.commandName)
    async def deleteModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.DeleterModerator): return

        if type(id) is str:
            id = self.__extractMemberIdFromString(id)

        if id is None:
            logging.info(f'{ctx.author}:{CommandProperty.DeleterModerator.commandName}:id is none:{id}')
            await ctx.send(CommandProperty.DeleterModerator.getFailedAnswer())
            return

        if not ( id in self.__allModers ):
            logging.info(f'{ctx.author}:{CommandProperty.DeleterModerator.commandName}:moderator not exist::{id}')
            await ctx.send(CommandProperty.DeleterModerator.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__allModers.remove(id)
            data["all_moderator"] = self.__allModers
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{ctx.author}:{CommandProperty.DeleterModerator.commandName}:moderator delete:{id}')
        await ctx.send(CommandProperty.DeleterModerator.getSuccessAnswer(None, id))

    @commands.command(name = CommandProperty.AdderSR.commandName)
    async def addModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.AdderModerator): return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        role = self.__guild.get_role(id)

        if type(role) is not discord.Role:
            logging.info(f'{ctx.author}:{CommandProperty.AdderSR.commandName}:id is none::{id}')
            await ctx.send(CommandProperty.AdderSR.getFailedAnswer())
            return

        if role in self.__startRoles:
            logging.info(f'{ctx.author}:{CommandProperty.AdderSR.commandName}:role exists::{id}')
            await ctx.send(CommandProperty.AdderSR.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__startRoles.append(role)
            data["start_roles"] = [role.id for role in self.__startRoles]
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{ctx.author}:{CommandProperty.AdderSR.commandName}:role add::{id}')
        await ctx.send(CommandProperty.AdderSR.getSuccessAnswer(role.name, id))

    @commands.command(name = CommandProperty.DeleterSR.commandName)
    async def deleteModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.DeleterSR): return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        if id is None:
            logging.info(f'{ctx.author}:{CommandProperty.DeleterSR.commandName}:id is none:{id}')
            await ctx.send(CommandProperty.DeleterSR.getFailedAnswer())
            return
        
        role = self.__guild.get_role(id)

        if not ( role in self.__startRoles ):
            logging.info(f'{ctx.author}:{CommandProperty.DeleterSR.commandName}:role not exist::{id}')
            await ctx.send(CommandProperty.DeleterSR.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__startRoles.remove(role)
            data["start_roles"] = [role.id for role in self.__startRoles]
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{ctx.author}:{CommandProperty.DeleterSR.commandName}:moderator delete:{id}')
        await ctx.send(CommandProperty.DeleterSR.getSuccessAnswer(role.name, id))

    @commands.command(name = CommandProperty.ShowStage.commandName)
    async def showStage(self, ctx: commands.Context, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.ShowStage): return

        info: str = '======Info======\n'

        info += f'Profile parse from {None if self.__profileChannel is None else self.__profileChannel.mention} -> {None if self.__profileParseInfoChannel is None else self.__profileParseInfoChannel.mention}\n'

        info += f'Resource parse from {None if self.__resourceChannel is None else self.__resourceChannel.mention}\n'

        info += 'Start role: '

        for role in self.__startRoles:

            info += f'{role.mention} '

        info += '\n'

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

    @commands.command(name = CommandProperty.Help.commandName)
    async def helpSWCommand(self, ctx: commands.Context, *args, member: discord.Member = None):
        if not self.__verifyAccess(ctx, CommandProperty.Help): return

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

    def __updateProfileParserInfoData(self):
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            data["profile_info_channel"] = None if self.__profileChannel is None else self.__profileChannel.id
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

    def __isPossibilities(self, ctx: commands.Context, name: str | None, id: int | None, targetCommandObject: CommandStuct, listForSearch: list):
        
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

    def addAdditionalThread(self, tempTread: TempThread):
        self.__additionalThread[tempTread.thread.id] = tempTread

    def removeAdditionalThread(self, threadId: int):
        if threadId in self.__additionalThread:
            try:
                del self.__additionalThread[threadId]
            except Exception: pass

    @property
    def clanLinks(self):
        return self.__clanLinks

    @property
    def moderatorsId(self):
        return ([] if self.__superModers is None else self.__superModers) + ([] if self.__allModers else self.__allModers)

    @property
    def startRole(self):
        return [] if self.__startRoles is None else self.__startRoles

    @commands.command(name = 'flip')
    async def flipMod(self, ctx: commands.Context, *, member: discord.Member = None):
        if ctx.author.id in self.__superModers:
            self.__superMod = not self.__superMod

            await ctx.send('Set super mod' if self.__superMod else 'Set noraml mod')

    async def __profileHandler(self, message: discord.Message) -> bool:

        # Check attachments quantity

        if not message.attachments:
            logging.info(f'{message.author}:profile parse:Failed! no attachment')
            return False

        # Check first attachment size

        if message.attachments[0].size > self.MAX_BUFFER_SIZE:
            logging.info(f'{message.author}:profile parse:Failed! size file')
            return False

        if not message.attachments[0].filename.endswith(('.png', '.jpeg', '.gif')):
            logging.info(f'{message.author}:profile parse:Failed! file not image')
            return False

        # Convert attachment to image

        buffer = BytesIO()

        try:
            await message.attachments[0].save(buffer)
            potentialProfileImage = Image.open(buffer)
        except Exception:
            logging.info(f'{message.author}:profile parse:Failed! save error')
            return False
        
        # Work with profile
        try:
            profileDecoder = MainProfileParser(potentialProfileImage)

            if not profileDecoder.isFullWithoutRank:
                logging.info(f'{message.author}:profile parse:Failed! image not parse')
                return False
        except Exception as e:
            logging.info(f'{message.author}:profile parse:Failed! {type(e).__name__}')
            return False

        potentialNameSelected = None
        for potentialName in message.content.split():
            if len(potentialName) > 3:
                potentialNameSelected = potentialName
                break

        if potentialNameSelected:

            if ratio(potentialNameSelected, profileDecoder.userName, processor = wordSimplificationEng) > self.MINIMUM_PART_MATHC:

                if self.__clanLinks[profileDecoder.clanName]['role']:
                    
                    await finishWithMember(message.author, f'[{self.__clanLinks[profileDecoder.clanName]["role"].name}] {potentialNameSelected}', self.__clanLinks[profileDecoder.clanName]['role'], message)

                    logging.info(f'{message.author}:profile parse:success')
                    return True
                
                else:

                    logging.info(f'{message.author}:profile parse:Failed! clan not has role')
                    return False

            else:

                logging.info(f'{message.author}:profile parse:Failed! names is different')
                return False
            
        else:

            thread = await message.create_thread(name = MessageForAnswers.HEADER_FOR_PROFILE_BRANCH)
            myView = NameQuestionnaireView(name = f'[{self.__clanLinks[profileDecoder.clanName]["role"].name}] {profileDecoder.userName}', role = self.__clanLinks['SacredWizardsVita']['role'], currentMessage = message, thread= thread)

            currentMessage = await thread.send(MessageForAnswers.QUESTION_ABOUT_POTANTIAL_NAME.format(profileDecoder.userName), view = myView)
            myView.messageWithButton = currentMessage

            return True
    
    async def __resourceHandler(self, message: discord.Message) -> bool:

        rank = attemptExtractRank( message.content )

        if rank is None:
            logging.info(f'{message.author}:resource parse:Failed! no extract rank')
            return False

        if len(message.attachments) == 0:
            logging.info(f'{message.author}:resource parse:Failed! no file')
            return False
        
        
        resourceCollect = {}
        respondMessage = f'Здравствуйте, {message.author}. Ваш ранг был определён как {rank}'

        quanityReourceValid = 0

        #TODO: check name
        for attachment in message.attachments:
            if attachment.size > self.MAX_BUFFER_SIZE:
                continue
            
            if not attachment.filename.endswith(('.png', '.jpeg', '.gif')):
                continue
            
            buffer = BytesIO()

            try:
                await attachment.save(buffer)
                potentialResourceImage = Image.open(buffer)
            except Exception:
                continue

            try:
                resourceDecoder = ResourceProfileParser(potentialResourceImage, rank, self.RESOURCE_QUANTITY_TYPE - quanityReourceValid)

                # if ratio(resourceDecoder.userName, message.author.name, processor = wordSimplificationEng) > self.MINIMUM_PART_MATHC:

                resourceCollect.update(resourceDecoder.resource)
                for resource, value in resourceDecoder.resource.items():

                    needResource = resource.getQuantityOnRank(rank)

                    if needResource <= value:

                        quanityReourceValid += 1
                        respondMessage += f'\n :white_check_mark: {resource.names["rus"]}: {value}/{needResource}'
                    else:
                        respondMessage += f'\n :x: {resource.names["rus"]}: {value}/{needResource}'


            except Exception as e:
                import traceback
                print(traceback.format_exc())
                continue

            if quanityReourceValid >= self.RESOURCE_QUANTITY_TYPE:
                break

        # If resource enough

        if quanityReourceValid >= self.RESOURCE_QUANTITY_TYPE:
            respondMessage += '\n\nВаш вклад удвлетворяет условию. Пожалуйста, дождитесь модератора из вашего клана.'
            tempThread = await message.create_thread(name = 'Успех')
            await tempThread.send(respondMessage)

            for links in self.__clanLinks.values():
                
                if links['role'] in message.author.roles:
                    
                    if links['alert_channel'] is not None:
                        tempMessage: discord.Message = await links['alert_channel'].send(f'1. {message.author} {message.author.mention}\n2. Magiaicn (2-ой способ)\n3. {rank} ранг',
                                                                        files = [await a.to_file() for a in message.attachments])
                        
                        self.__reportLink[tempMessage.id] = (message, tempThread)
                        await tempMessage.add_reaction('✅')
                        break

            return True
        
        # If resource not enough
        respondMessage += '\n\nВаш вклад НЕ удвлетворяет условию. Вы согласны?'

        tempThread = await message.create_thread(name = 'Провал')
        for clanLink in self.__clanLinks.values():
            if clanLink['role'] in message.author.roles:
                await tempThread.send(respondMessage, view= ResourceQuestionnaireView(currentMessage= message, thread= tempThread, moderChannelForHelp = clanLink['alert_channel']))
                break

        return False


    async def __additionalThreadHandler(self, message: discord.Message, tempThread: TempThread) -> bool:
        potentialName = message.content.strip()

        if len(potentialName) < 4 or tempThread.currentMessage.author is message.author:
            return
        
        if potentialName.startswith('`'):
            potentialName = potentialName[1:]

        if potentialName.endswith('`'):
            potentialName = potentialName[:-1]

        if ratio(potentialName, tempThread.name, processor = wordSimplificationEng) > self.MINIMUM_PART_MATHC:
            await finishWithMember(message.author, potentialName, tempThread.role, tempThread.currentMessage, tempThread.thread)
            return True

        tempThread.view.setNamesTooDifferent()
        return False


ALL_COGS = [SWCog]