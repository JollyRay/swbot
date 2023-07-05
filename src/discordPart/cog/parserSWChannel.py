import discord
from discord.ext import commands
import asyncio
import json
import logging
import re
from io import BytesIO
from PIL import Image
from parser.profileParser import MainProfileParser, ResourceProfileParser, wordSimplificationEng
from Levenshtein import ratio
from asyncio import sleep 
from collections.abc import Iterable
from enum import Enum

swBot = None
PREFIX = '♂'

def setup(outerBot: commands.Bot, prefix: str) -> commands.bot:
    global swBot
    global PREFIX

    PREFIX = prefix
    swBot = outerBot
        
    @swBot.check
    async def globallyBlockAnonymousUser(ctx):
        if ctx.author is None:
            logging.info('None:None:message from non-user')
            return False
        return True

    for cog in ALL_COGS:
        asyncio.run(swBot.add_cog(cog(swBot)))

#################################
#                               #
#             UTIL              #
#                               #
#################################

# Sec
TIMEOUT_BEFORE_DELETE = 180

ACCEPT_SYMBLE = '✅'
REFUSE_SYMBLE = '❌'

CAN_DELETE = False

class _MessageAfterProfileParse(str, Enum):

    CORRECT_PARSE = ''
    UNFIND_IMAGE = 'Вы не прикрепили изображение профиля. Отправьте его в ЭТУ ветку.'
    UNCORRECT_IMAGE = 'Выше изображение не вышло обработать, пожалуйста дождитесь модератора. Сообщение им уже отправлено!'
    UNCORRECT_HEADER = 'Не удалось извелечь ваш ник из заголовка. С изображения был считан "{name}" этот ник совпадает с вашим?'
    UNCORRECT_HEADER_IF_IMAGE_PARSE_UNCCORECT = 'Напишите в ЭТУ ветку ваш ник без постфкиса после # (Решётку тоже не надо!).'
    UNCORRECT_MESSAGE = 'Ваше сообщение не соответсвует форме. Поажлуйста, оформите ваше сообщение как в примере.'
    UNCORRECT_SCRIPT = 'Извлечённый ник и указанный вами слишком сильно разнятся, пожалуйста дождитесь модератора. Оповещение им уже отправлено!'

    UNCORRECT_IMAGE_REPORT = '{name.mention} get unparsable image. Need moderator.'
    UNCORRECT_SCRIPT_REPORT = '{name.mention} wrong ratio. Need moderator.'

class _MessageAfterResourseParse(str, Enum):

    TIMEOUT_RESPOND = 'Прошло слишком много времени. Заполните новую форму или обратитесь к модераторам.'
    UNCORRECT_IMAGE = 'Ваше изображение странного формата. Отправлен запрос модерации для обработки.'
    MISSING_IMAGE = 'Прикрепите изображени вашего вклада (ESC - Связь - Клан ПКМ по себе "Внесённый вклад")'
    MISSING_RANK = 'Неудалось получить вашн ранг. Пожалуйста напишите сюда его одним числом.'
    NEED_MORE_RESOURCE = 'Ваш вклад не соответствует условию:{resource}\n\nБот распарсил верно?'
    UNCORRECT_USER_DATA = 'Если вы считаете, что бот ошибся, мы отправили оповещение вашим модераторам оповещение.'
    UNCORRECT_SCRIPT = 'Ваша ситуация передаётся под управлению модераторм. Сообщением им уже отправлено, пожалуйста подождите.'
    CORRECT_ALL = 'Ваши данные обработаны и корректны. Повышение санкионировано, пожалуйста дождитесь модератора вашего клана в игре, оповещение им уже отправлено.'

    UNCORRECT_IMAGE_REPORT = '{member.mention} (из {channel.mention}) отправил странное изображение, не могу обработать.'
    # UNCORRECT_USER_DATA_REPORT = '{member.mention} (из {channel.mention}) считает что бот распрасил данные неверно.'
    UNCORRECT_SCRIPT_REPORT = '{member.mention} (из {channel.mention}) отправил сообщение, которое не вышло обработать'

    MAGICIAN_REPORT = '''1. {name} {authorMention}
2. Magician (2-ой способ)
3. {rank} ранг
:white_check_mark: - отчёт корректен, подчистить треды.
:x: - удалить отчёт'''
    NAME_WARNING = 'Возможно имя не соответсвует хозяину ресурсов!'

class _CommandStuct:
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

        return self._createDescription(prefix, *args)
    
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

class _CommandProperty:
    def __new__(cls,*args):
        if cls is _CommandProperty:
            return None
        return object.__new__(cls,*args)
    
    SetterCFPI: _CommandStuct = _CommandStuct(
        name = 'setCFPI',
        createDescription = lambda prefix: '%ssetCFPI <id> - set channel for info about error channel' % (prefix),
        createSuccessfulExecutionMessage = lambda name, id: 'Channel for error is removed' if id is None else 'Channel "%s"(%s) is selected for error' % (name, id),
        createFailedExecutionMessage = lambda _ = None, id = None: 'Channel (%s) is not found' % id
    )
    SetterCFP: _CommandStuct = _CommandStuct(
        name = 'setCFP',
        createDescription = lambda prefix: '%ssetCFP <id> - set channel for parse profile & set clan role' % (prefix),
        createSuccessfulExecutionMessage = lambda name, id: 'Channel for profile parse is removed' if id is None else 'Channel "%s"(%s) is selected for profile parse' % (name, id),
        createFailedExecutionMessage = lambda _ = None, id = None: 'Channel (%s) is not found' % id
    )
    SetterCFR: _CommandStuct = _CommandStuct(
        name = 'setCFR',
        createDescription = lambda prefix: '%ssetCFR <id> - set channel for parse profile on resource' % (prefix),
        createSuccessfulExecutionMessage = lambda name, id: 'Channel for resource parse is removed' if id is None else 'Channel "%s"(%s) is selected for resource parse' % (name, id),
        createFailedExecutionMessage = lambda _ = None, id = None: 'Channel (%s) is not found' % id
    )
    SetterCFA: _CommandStuct = _CommandStuct(
        name = 'setCFA',
        createDescription = lambda prefix: '%ssetCFA <clan name> <id> - set channel for alert' % (prefix),
        createSuccessfulExecutionMessage = lambda channelName, channelId = None: 'Alert (for %s) wont send' % channelName if channelId is None else 'Alert will send to channel %s (%s)' % (channelName, channelId),
        createFailedExecutionMessage = lambda channelName = None, id = None: 'Clan not found' % channelName if id is None else 'Channel (%s) is not found' % id
    )
    SetterCRI: _CommandStuct = _CommandStuct(
        name = 'setCRI',
        createDescription = lambda prefix: '%ssetCRI <clan name> <id> - set role for clan' % (prefix),
        createSuccessfulExecutionMessage = lambda clanName, roleId: 'Remove role for %s' % clanName if roleId is None else 'Connect role %s with clan %s' % (roleId, clanName),
        createFailedExecutionMessage = lambda clanName, _ = None: 'Clan not found' if clanName is None else 'Cant connect clan with role'
    )
    SetterSCR: _CommandStuct = _CommandStuct(
        name = 'setSCR',
        createDescription = lambda prefix: '%ssetSCR <id> - set role without clan' % (prefix),
        createSuccessfulExecutionMessage = lambda _, roleId: 'Remove role' if roleId is None else 'Set role %s without clan' % roleId,
        createFailedExecutionMessage = lambda *_: 'Cant remove'
    )
    AdderC: _CommandStuct = _CommandStuct(
        name = 'addC',
        createDescription = lambda prefix: '%saddC <clan name> - add clan' % (prefix),
        createSuccessfulExecutionMessage = lambda clanName, _ = None: 'Add new clan "%s' % (clanName),
        createFailedExecutionMessage = lambda clanName = None, _ = None: 'Title not specified' if clanName is None else '%s exists' % (clanName)
    )
    DeleterC: _CommandStuct = _CommandStuct(
        name = 'delC',
        createDescription = lambda prefix: '%sdelC <clan name> - delete clan' % (prefix),
        createSuccessfulExecutionMessage = lambda clanName, _ = None: 'Clan (%s) is deleted' % (clanName),
        createFailedExecutionMessage = lambda clanName, _ = None: 'Clan name is none' if clanName is None else 'Clan (%s) is not found' % (clanName),
    )
    AdderModerator: _CommandStuct = _CommandStuct(
        name = 'addM',
        createDescription = lambda prefix: '%saddM <user id> - add moderator to list' % (prefix),
        createSuccessfulExecutionMessage = lambda _ = None, userId = None: 'Moderator (%s) is added to moder list' % (userId),
        createFailedExecutionMessage = lambda _ = None, userId = None: 'Id is not id format' if userId is None else '%s exists' % (userId)
    )
    DeleterModerator: _CommandStuct = _CommandStuct(
        name = 'delM',
        createDescription = lambda prefix: '%sdelM <user id> - delete moderator from list' % (prefix),
        createSuccessfulExecutionMessage = lambda _ = None, userId = None: 'Moderator (%s) is deleted from moder list' % (userId),
        createFailedExecutionMessage = lambda userId:'Id is not id format' if userId is None else '%s not exist'
    )
    AdderSR: _CommandStuct = _CommandStuct(
        name = 'addSR',
        createDescription = lambda prefix: '%saddSR <role id> - add start role' % (prefix),
        createSuccessfulExecutionMessage = lambda roleName = None, _ = None: 'Add role (%s)' % (roleName),
        createFailedExecutionMessage = lambda _ = None, userId = None: 'Id is not id format' if userId is None else '%s exists' % (userId)
    )
    DeleterSR: _CommandStuct = _CommandStuct(
        name = 'delSR',
        createDescription = lambda prefix: '%sdelSR <role id> - delete start role' % (prefix),
        createSuccessfulExecutionMessage = lambda roleName = None, _ = None: 'Delete role (%s)' % (roleName),
        createFailedExecutionMessage = lambda _ = None, userId = None: 'Id is not id format' if userId is None else '%s exists' % (userId)
    )
    ShowStage: _CommandStuct = _CommandStuct(
        name = 'show',
        createDescription = lambda prefix: '%sshow - show all info' % (prefix)
    )
    Help: _CommandStuct = _CommandStuct(
        name = 'help'
    )

class _TempThreadWithData:

    def __init__(self, code: _MessageAfterProfileParse | None = None, currentMessage: discord.Message | None = None, currentTread: discord.Thread | None = None, listOfPotensialNames: list[str] | None = None) -> None:
        
        self.code = code
        self.currentMessage = currentMessage
        self.currentThread = currentTread

        self.listOfPotensialNames = listOfPotensialNames

async def _setClanRoleForMember(member: discord.Member, role: discord.Role):

    try:
        for clanLinks in swBot.cogs['SWDataCog'].clanLinks.values():

            if clanLinks['role'] in member.roles:

                await member.remove_roles(clanLinks['role'])

        for startRole in swBot.cogs['SWDataCog'].startRole:

            if startRole in member.roles:

                await member.remove_roles(startRole)

        await member.remove_roles(swBot.cogs['SWDataCog'].roleWithoutClan)

        if role is not None:
            await member.add_roles(role)

    except Exception:

        logging.info('::cant set role')

async def finishWithMember(author: discord.Member = None, name: str = None, role: discord.Role = None, currentMessage: Iterable[discord.Message] | discord.Message = None, thread: Iterable[discord.Thread] | discord.Thread = None):
    if all((author, role)):
        await _setClanRoleForMember(author, role)

    if all((author, name)):
        try:
            await author.edit( nick = name)
        except Exception: pass

    if CAN_DELETE:

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

async def _converAttachmentToImage(attachment: discord.Attachment):
    try:
        buffer = BytesIO()
        await attachment.save(buffer)
        return Image.open(buffer)
    except Exception:
        return None

def attemptExtractRank(comment: str) -> int:

    # Standart

    if comment.isdigit():
        return int(comment)
    elif len(comment) > 4:

        isLegendary = comment.find('лег') >= 0

        allNumbersInComment = re.findall( r'[^-._a-zA-Z0-9]\d{1,2}[ -]', comment )

        if len(allNumbersInComment) == 1:
            return int(allNumbersInComment[0][1:-1]) + 30 * isLegendary
        
        if len(allNumbersInComment) > 1:
            
            for i in range(6):
                if int(allNumbersInComment[i][1:-1]) != i:
                    return int(allNumbersInComment[i][1:-1]) + 30 * isLegendary
    
    # On indexed rows

    lines = comment.split('\n')[1:]

    for line in lines:

        if line.startswith('2'):

            stringOfRank = re.search(r'[1-9]\d{0,1}', line[1:])

            if stringOfRank is None:
                return None
            
            return int(stringOfRank.group())


    return None

def extractNameWithouClan(fullName: str):
    tagIndex = fullName.find(']')
    return fullName if tagIndex == -1 else fullName[tagIndex + 1:].strip()

def puckReportMessage(currentMessage: discord.Message, isNameWarning: bool, rank: int, infoAboutResource: str):
    respond: str =  _MessageAfterResourseParse.MAGICIAN_REPORT.value.format(
        name = extractNameWithouClan(currentMessage.author.name) if currentMessage.author.nick is None else extractNameWithouClan(currentMessage.author.nick),
        authorMention = currentMessage.author.mention,
        rank = rank
        )
    if isNameWarning:
        respond += f'\n{_MessageAfterResourseParse.NAME_WARNING.value}'

    if infoAboutResource:
        respond += infoAboutResource

    return respond

async def sendRespondAndReport(currentMessage: discord.Message, currentThread: discord.Thread, attachment: list[discord.Attachment], clanChannel: discord.TextChannel, meesageForUser: str, reportMessage: str):

    if currentThread is not None:
        await currentThread.send(meesageForUser)

    if clanChannel is None:
        return

    message: discord.Message = await clanChannel.send(reportMessage, files= [await a.to_file() for a in attachment])
    await message.add_reaction(ACCEPT_SYMBLE)
    await message.add_reaction(REFUSE_SYMBLE)

    swBot.cogs['SWUserCog'].addResourceLinks(message, _MessageAfterResourseParse.UNCORRECT_USER_DATA, currentMessage, currentThread)

async def replyAndAlarm(messageForReply: discord.Message, forUser: str, forModers: str | None = None, isDelete: bool = False):
    try:
        if isDelete:
            await messageForReply.reply(forUser, delete_after = TIMEOUT_BEFORE_DELETE)
        else:
            await messageForReply.reply(forUser)
    except discord.HTTPException:
        if isinstance(messageForReply.channel, discord.Thread):
            logging.info(f'::{swBot.cogs["SWUserCog"].CANT_SEND_TO_PROFILE_THREAD}')
        else:
            logging.info(f'::{swBot.cogs["SWUserCog"].CANT_SEND_TO_PROFILE_CHANNEL}')

    if forModers:
        try:
            await swBot.cogs['SWDataCog'].profileParseReportChannel.send(forModers)
        except discord.HTTPException:
            logging.info(f'::{swBot.cogs["SWUserCog"].CANT_SEND_TO_MODER_CHAT}')

#################################
#                               #
#           Discord             #
#                               #
#################################

class BaseWithButtonView(discord.ui.View):

    def __init__(self, *_):
        super().__init__(timeout = TIMEOUT_BEFORE_DELETE)

        self.__messageWithButton: discord.Message | None = None

    async def on_timeout(self):
        await self._disableAllButton()

    async def _disableAllButton(self):

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.__messageWithButton is None:
            await sleep(1)
            if self.__messageWithButton is None:
                return
        try:
            await self.__messageWithButton.edit(view = self)
        except discord.NotFound:
            pass
            
    @property
    def messageWithButton(self):
        return self.__messageWithButton
    
    @messageWithButton.setter
    def messageWithButton(self, newMessage):
        self.__messageWithButton = newMessage

class ResourceParserQuestion(BaseWithButtonView):

    def __init__(self, *, currentMessage: discord.Message, currentThread: discord.Thread, rank: int, attachment: list[discord.Attachment], clanChannel, isNameWaringn: bool = False, infoAboutResource: str =''):
        super().__init__()

        self.__currentMessage = currentMessage
        self.__currentThread = currentThread
        self.__rank = rank
        self.__attachments = attachment
        self.__clanChannel = clanChannel
        self.__isNameWaringn = isNameWaringn
        self.__infoAboutResource = infoAboutResource

    @discord.ui.button( label = 'Да', style = discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, _: discord.Button):
        if self.__currentMessage.author.id != interaction.user.id:
            await interaction.response.defer()
            return
        await interaction.response.defer()
        await finishWithMember(currentMessage = self.__currentMessage, thread = self.__currentThread)

    @discord.ui.button( label = 'Нет', style = discord.ButtonStyle.red)
    async def refuse(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer()
        if self.__currentMessage.author.id != interaction.user.id:
            return
        await self._disableAllButton()
        reportMessage = puckReportMessage(self.__currentMessage, self.__isNameWaringn, self.__rank, self.__infoAboutResource)
        await sendRespondAndReport(self.__currentMessage, self.__currentThread, self.__attachments, self.__clanChannel, _MessageAfterResourseParse.UNCORRECT_USER_DATA.value, reportMessage)

class ProfileMessageWithoutHeaderView(BaseWithButtonView):

    def __init__(self, *, nameFromImage: str, role: discord.Role, currentMessage: discord.Message):
        super().__init__(timeout = TIMEOUT_BEFORE_DELETE)

        self.__name: str = nameFromImage
        self.__role: discord.Role = role
        self.__currentMessage: discord.Message = currentMessage
        self.__thread: discord.Thread = None

        self.__isPushing = False

    async def on_timeout(self):

        if not self.__isPushing:
            await finishWithMember(currentMessage = self.__currentMessage, thread = self.__thread)

        swBot.cogs['SWUserCog'].deleteThreadListener(self.__thread)

    @discord.ui.button( label = 'Да', style = discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.Button):
        
        if self.__currentMessage.author.id is interaction.user.id:
            self.__isPushing = True

            await interaction.response.defer()
            await self._disableAllButton()
            await finishWithMember(self.__currentMessage.author, f'[{self.__role.name}] {self.__name}', self.__role, self.__currentMessage, self.__thread)
        else:
            await interaction.response.defer()

    @discord.ui.button( label = 'Нет', style = discord.ButtonStyle.red)
    async def refuse(self, interaction: discord.Interaction, button: discord.Button):

        if self.__currentMessage.author.id is interaction.user.id:
            self.__isPushing = True

            await self._disableAllButton()

            swBot.cogs['SWUserCog'].addThreadListener(
                self.__thread.id,
                _TempThreadWithData(
                    _MessageAfterProfileParse.UNCORRECT_HEADER,
                    self.__currentMessage,
                    self.__thread,
                    [self.__name , self.__role]
                )
            )
            
            await interaction.response.send_message(_MessageAfterProfileParse.UNCORRECT_HEADER_IF_IMAGE_PARSE_UNCCORECT.value)
        else:
            await interaction.response.defer()

    @property
    def thread(self):
        return self.__thread
    
    @thread.setter
    def thread(self, newThread):
        self.__thread = newThread

class SWCog(commands.Cog, name='SWDataCog'):

    #############################
    #                           #
    #       SET ALL DATA        #
    #                           #
    #############################

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

            if 'role_without_clan' in data.keys():
                self.__roleWithoutClan: discord.Role = self.__guild.get_role(data['role_without_clan'])
            else:
                logging.warning('::WARING! Missing key "all_moderator"')
                self.__roleWithoutClan: discord.Role = None

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
                self.__profileParseReportChannel: discord.TextChannel = self.__guild.get_channel(data['profile_info_channel'])
            else:
                logging.warning('::WARING! Missing key "profile_info_channel"')
                self.__profileParseReportChannel: discord.TextChannel = None
                
            self.__profileChannel: discord.TextChannel | None = None if data.get('profile_channel', None) is None else self.__guild.get_channel(data['profile_channel'])
            if self.__profileChannel is None:
                logging.warning('::WARING! Undefind "profile_channel"')

            self.__resourceChannel: discord.TextChannel | None = None if data.get('resource_channel', None) is None else self.__guild.get_channel(data['resource_channel'])
            if self.__resourceChannel is None:
                logging.warning('::WARING! Undefind "resource_channel"')

        self.__updateAllData()

        print('#' * 44, '', f'\tLogged on as {self.bot.user}!', '', '#' * 44, sep = '\n')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        
        if type(error) is commands.CommandNotFound:
            logging.warning(f'{ctx.author.name}::{error}')

    #############################
    #                           #
    #       DATA UTILITY        #
    #                           #
    #############################

    def __updateAllData(self):
        self.__updateClanData()
        self.__updateProfileParserData()
        self.__updateRoleWithoutClan()
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

    def __updateRoleWithoutClan(self):
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            data["role_without_clan"] = None if self.__roleWithoutClan is None else self.__roleWithoutClan.id
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

    __extractRoleIdFromSting = staticmethod(lambda id: id if re.match(r'^<@&\d{10,20}>$', id) is None else int(id[3:-1]))
    __extractChannelIdFromString = staticmethod(lambda id: id if re.match(r'^<#\d{10,20}>$', id) is None else int(id[2:-1]))
    __extractMemberIdFromString = staticmethod(lambda id: id if re.match(r'^<@\d{10,20}>$', id) is None else int(id[2:-1]))

    #################
    #               #
    #   PROPERTY    #
    #               #
    #################

    @property
    def clanLinks(self):
        return self.__clanLinks
    
    @property
    def roleWithoutClan(self):
        return self.__roleWithoutClan

    @property
    def moderatorsId(self):
        return ([] if self.__superModers is None else self.__superModers) + ([] if self.__allModers else self.__allModers)

    @property
    def startRole(self):
        return [] if self.__startRoles is None else self.__startRoles

    @property
    def profileParseReportChannel(self):
        return self.__profileParseReportChannel

    @property
    def profileParseChannel(self):
        return self.__profileChannel
    
    @property
    def resourceChannel(self):
        return self.__resourceChannel

    #################################
    #                               #
    #       MODERATOR COMMAND       #
    #                               #
    #################################

    @commands.command(name = _CommandProperty.SetterCFPI.commandName)
    async def setChannelForProfileParserInfo(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):

        if type(id) is str:
            id = self.__extractChannelIdFromString(id)

        isPossible, message = self.__isPossibilities(ctx, None, id, _CommandProperty.SetterCFPI, self.__guild.text_channels)

        if isPossible:
        
            self.__profileParseReportChannel = self.__guild.get_channel(id)
            self.__updateProfileParserInfoData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = _CommandProperty.SetterCFP.commandName)
    async def setChannelForProfileParser(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if type(id) is str:
            id = self.__extractChannelIdFromString(id)
        isPossible, message = self.__isPossibilities(ctx, None, id, _CommandProperty.SetterCFP, self.__guild.text_channels)

        if isPossible:
        
            self.__profileChannel = self.__guild.get_channel(id)
            self.__updateProfileParserData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = _CommandProperty.SetterCFR.commandName)
    async def setChannelForProfileResource(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if type(id) is str:
            id = self.__extractChannelIdFromString(id)
        isPossible, message = self.__isPossibilities(ctx, None, id, _CommandProperty.SetterCFR, self.__guild.text_channels)

        if isPossible:
            
            self.__resourceChannel = self.__guild.get_channel(id)
            self.__updateResourceParserData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = _CommandProperty.SetterCFA.commandName)
    async def setChannelForAlert(self, ctx: commands.Context, clanName: str, id: int | str = None, *, member: discord.Member = None):

        if not (clanName in self.__clanLinks.keys()) :
            logging.info(f'{ctx.author}:{_CommandProperty.SetterCFA.commandName}:clan not found:{clanName}:{id}')
            await ctx.send(_CommandProperty.SetterCFA.getFailedAnswer(clanName, id))
            return

        if type(id) is str:
            id = self.__extractChannelIdFromString(id)
        isPossible, message = self.__isPossibilities(ctx, clanName, id, _CommandProperty.SetterCFA, self.__guild.text_channels)

        if isPossible:

            self.__clanLinks[clanName]['alert_channel'] = self.__guild.get_channel(id)
            self.__updateClanData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = _CommandProperty.SetterCRI.commandName)
    async def setClanRoleId(self, ctx: commands.Context, clanName: str, id: int | str = None, *, member: discord.Member = None):

        if not (clanName in self.__clanLinks.keys()):
            logging.info(f'{ctx.author}:{_CommandProperty.SetterCRI.commandName}:clan not found:{clanName}:{id}')
            await ctx.send(_CommandProperty.SetterCRI.getFailedAnswer(None))
            return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        isPossible, message = self.__isPossibilities(ctx, clanName, id, _CommandProperty.SetterCRI, self.__guild.roles)

        if isPossible:
            
            self.__clanLinks[clanName]['role'] = self.__guild.get_role(id)
            self.__updateClanData()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = _CommandProperty.SetterSCR.commandName)
    async def setRoleWithoutClan(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        isPossible, message = self.__isPossibilities(ctx, None, id, _CommandProperty.SetterSCR, self.__guild.roles)

        if isPossible:
            
            self.__roleWithoutClan = self.__guild.get_role(id)
            self.__updateRoleWithoutClan()

        if not (message is None):
            await ctx.send(message)

    @commands.command(name = _CommandProperty.AdderC.commandName)
    async def addClan(self, ctx: commands.Context, clanName: str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, _CommandProperty.AdderC): return

        if clanName is None:
            logging.info(f'{ctx.author}:{_CommandProperty.AdderC.commandName}:clan is none:{clanName}')
            ctx.send(_CommandProperty.AdderC.getFailedAnswer())
            return

        if clanName.lower() in [clan.lower() for clan in self.__clanLinks.keys()]:
            logging.info(f'{ctx.author}:{_CommandProperty.AdderC.commandName}:clan exists:{clanName}')
            await ctx.send(_CommandProperty.AdderC.getFailedAnswer(clanName))
            return
        
        self.__clanLinks[clanName] = {'role': None, 'alert_channel': None}
        self.__updateClanData()

        logging.info(f'{ctx.author}:{_CommandProperty.AdderC.commandName}:clan add:{clanName}')
        await ctx.send(_CommandProperty.AdderC.getSuccessAnswer(clanName))

    @commands.command(name = _CommandProperty.DeleterC.commandName)
    async def deleteClan(self, ctx: commands.Context, clanName: str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, _CommandProperty.DeleterC): return

        if clanName is None:
            logging.info(f'{ctx.author}:{_CommandProperty.DeleterC.commandName}:clan is none:{clanName}')
            await ctx.send(_CommandProperty.DeleterC.getFailedAnswer())
            return

        if not (clanName.lower() in [clan.lower() for clan in self.__clanLinks.keys()]):
            logging.info(f'{ctx.author}:{_CommandProperty.DeleterC.commandName}:clan not exist:{clanName}')
            await ctx.send(_CommandProperty.DeleterC.getFailedAnswer(clanName))
            return
        
        del self.__clanLinks[clanName]
        self.__updateClanData()

        logging.info(f'{ctx.author}:{_CommandProperty.DeleterC.commandName}:clan delete:{clanName}')
        await ctx.send(_CommandProperty.DeleterC.getSuccessAnswer(clanName))

    @commands.command(name = _CommandProperty.AdderModerator.commandName)
    async def addModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, _CommandProperty.AdderModerator): return

        if type(id) is str:
            id = self.__extractMemberIdFromString(id)

        if type(id) is not int:
            logging.info(f'{ctx.author}:{_CommandProperty.AdderModerator.commandName}:id is none::{id}')
            await ctx.send(_CommandProperty.AdderModerator.getFailedAnswer())
            return

        if id in self.__allModers:
            logging.info(f'{ctx.author}:{_CommandProperty.AdderModerator.commandName}:moderator exists::{id}')
            await ctx.send(_CommandProperty.AdderModerator.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__allModers.append(id)
            data["all_moderator"] = self.__allModers
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{ctx.author}:{_CommandProperty.AdderModerator.commandName}:moderator add::{id}')
        await ctx.send(_CommandProperty.AdderModerator.getSuccessAnswer(None, id))

    @commands.command(name = _CommandProperty.DeleterModerator.commandName)
    async def deleteModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, _CommandProperty.DeleterModerator): return

        if type(id) is str:
            id = self.__extractMemberIdFromString(id)

        if id is None:
            logging.info(f'{ctx.author}:{_CommandProperty.DeleterModerator.commandName}:id is none:{id}')
            await ctx.send(_CommandProperty.DeleterModerator.getFailedAnswer())
            return

        if not ( id in self.__allModers ):
            logging.info(f'{ctx.author}:{_CommandProperty.DeleterModerator.commandName}:moderator not exist::{id}')
            await ctx.send(_CommandProperty.DeleterModerator.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__allModers.remove(id)
            data["all_moderator"] = self.__allModers
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{ctx.author}:{_CommandProperty.DeleterModerator.commandName}:moderator delete:{id}')
        await ctx.send(_CommandProperty.DeleterModerator.getSuccessAnswer(None, id))

    @commands.command(name = _CommandProperty.AdderSR.commandName)
    async def addModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, _CommandProperty.AdderModerator): return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        role = self.__guild.get_role(id)

        if type(role) is not discord.Role:
            logging.info(f'{ctx.author}:{_CommandProperty.AdderSR.commandName}:id is none::{id}')
            await ctx.send(_CommandProperty.AdderSR.getFailedAnswer())
            return

        if role in self.__startRoles:
            logging.info(f'{ctx.author}:{_CommandProperty.AdderSR.commandName}:role exists::{id}')
            await ctx.send(_CommandProperty.AdderSR.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__startRoles.append(role)
            data["start_roles"] = [role.id for role in self.__startRoles]
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{ctx.author}:{_CommandProperty.AdderSR.commandName}:role add::{id}')
        await ctx.send(_CommandProperty.AdderSR.getSuccessAnswer(role.name, id))

    @commands.command(name = _CommandProperty.DeleterSR.commandName)
    async def deleteModerator(self, ctx: commands.Context, id: int | str = None, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, _CommandProperty.DeleterSR): return

        if type(id) is str:
            id = self.__extractRoleIdFromSting(id)

        if id is None:
            logging.info(f'{ctx.author}:{_CommandProperty.DeleterSR.commandName}:id is none:{id}')
            await ctx.send(_CommandProperty.DeleterSR.getFailedAnswer())
            return
        
        role = self.__guild.get_role(id)

        if not ( role in self.__startRoles ):
            logging.info(f'{ctx.author}:{_CommandProperty.DeleterSR.commandName}:role not exist::{id}')
            await ctx.send(_CommandProperty.DeleterSR.getFailedAnswer(None, id))
            return
        
        with open('resource/data.json', 'r+', encoding='utf-8') as dataFile:

            data: dict[str, any] = json.load( dataFile )
            self.__startRoles.remove(role)
            data["start_roles"] = [role.id for role in self.__startRoles]
            dataFile.seek(0)
            dataFile.truncate(0)
            json.dump(data, dataFile, ensure_ascii = False, indent = 4)

        logging.info(f'{ctx.author}:{_CommandProperty.DeleterSR.commandName}:moderator delete:{id}')
        await ctx.send(_CommandProperty.DeleterSR.getSuccessAnswer(role.name, id))

    @commands.command(name = _CommandProperty.ShowStage.commandName)
    async def showStage(self, ctx: commands.Context, *, member: discord.Member = None):
        if not self.__verifyAccess(ctx, _CommandProperty.ShowStage): return

        info: str = '======Info======\n'

        info += f'Profile parse from {None if self.__profileChannel is None else self.__profileChannel.mention} -> {None if self.__profileParseReportChannel is None else self.__profileParseReportChannel.mention}\n'

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

        info += f'Without clna ({self.__roleWithoutClan if self.__roleWithoutClan is None else self.__roleWithoutClan.mention})'

        await ctx.send(info)

    @commands.command(name = 'flip')
    async def flipMod(self, ctx: commands.Context, *, member: discord.Member = None):
        if ctx.author.id in self.__superModers:
            self.__superMod = not self.__superMod

            await ctx.send('Set super mod' if self.__superMod else 'Set noraml mod')

    @commands.command(name = _CommandProperty.Help.commandName)
    async def helpSWCommand(self, ctx: commands.Context, *args, member: discord.Member = None):
        if not self.__verifyAccess(ctx, _CommandProperty.Help): return

        commandDiscript = '====Command===='

        for commandName, commandProperty in vars(_CommandProperty).items():
            if not commandName.startswith('__'):
                discription = commandProperty.getDescription(PREFIX)
                if discription:
                    commandDiscript += f'\n{discription}'

        await ctx.send(commandDiscript)

    def __verifyAccess(self, ctx: commands.Context, targetCommandObject: _CommandStuct) -> bool:
        if ctx.author.id in self.__allModers or ctx.author.id in self.__superMod:
            return True
        logging.info(f'{ctx.author.name}:{targetCommandObject.commandName}:message from common user')
        return False

    def __isPossibilities(self, ctx: commands.Context, name: str | None, id: int | None, targetCommandObject: _CommandStuct, listForSearch: list):
        
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

#############################
#                           #
#       USER HANDLER        #
#                           #
#############################

class SWUserCog(commands.Cog, name='SWUserCog'):

    def __init__(self, clinet: commands.Bot):
        self.bot = clinet
        self.__dataCog: SWCog = clinet.cogs['SWDataCog']
        
        self.__threadForClarifications: dict[int, _TempThreadWithData] = {}
        self.__reportAndUserDataLink: dict[discord.Message, _TempThreadWithData] = {}

    @commands.Cog.listener()
    async def on_thread_remove(self, thread: discord.Thread):

        self.deleteThreadListener(thread)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        
        message: discord.Message | None = discord.utils.find(lambda message: message.id == payload.message_id, self.__reportAndUserDataLink.keys())
        if message:
    
            if payload.emoji.name == ACCEPT_SYMBLE:
                stringIndex = message.content.find('\n:white_check_mark:')
                if stringIndex != -1:
                    await message.edit(content = message.content[:stringIndex])
                    await finishWithMember(currentMessage = self.__reportAndUserDataLink[message].currentMessage, thread = self.__reportAndUserDataLink[message].currentThread)
                    await message.clear_reactions()
                    self.deleteReportLink(message)

            if payload.emoji.name == REFUSE_SYMBLE:
                await finishWithMember(currentMessage=message)
                self.deleteReportLink(message)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.content.startswith(PREFIX):
            return

        if message.author == self.bot.user:
            return

        if message.channel is self.bot.cogs['SWDataCog'].profileParseChannel:
            await self.__profileHandler(message)
            return
        
        if message.channel is self.__dataCog.resourceChannel:
            await self.__resourceParser(message)
            return
        

        if message.channel.id in self.__threadForClarifications:
            isNeedLate = await self.__extraThreadHandler(message, self.__threadForClarifications.get(message.channel.id))

            if not isNeedLate:
                del self.__threadForClarifications[message.channel.id]
            return

    MINIMUM_PART_MATCH = 0.75
    RESOURCE_QUANTITY_TYPE = 2

    #################################
    #                               #
    #       Main Profile Parse      #
    #                               #
    #################################
    
    CANT_SEND_TO_MODER_CHAT = 'cant moder chat'
    CANT_SEND_TO_PROFILE_THREAD = 'cant write to profile thread'
    CANT_SEND_TO_PROFILE_CHANNEL = 'cant write to profile channel'
    CANT_SEND_TO_RESOURCE_THREAD = 'cant write to resource thread'
    CANT_SEND_TO_RESOURCE_CHANNEL = 'cant write to resource channel'
    CANT_DELETE_THREAD = 'cant delete thread'
    CANT_DELETE_MESSAGE = 'cant delete message'

    async def __profileHandler(self, message: discord.Message):

        if message.content.lower().find('я хочу вступить в') != -1: return

        listOfPotansialNick = self.__extractNameFromProfileMessage(message.content)

        isHeaderMissing = len(listOfPotansialNick) == 0
        isImageMissing = len(message.attachments) == 0

        if isHeaderMissing and isImageMissing:

            await self.__uncorrectMessageRespond(message)
            return
        
        if isHeaderMissing:

            await self.__uncorrectHeaderRespond(message)
            return
        
        if isImageMissing:

            await self.__unfindImageRespond(message, listOfPotansialNick)
            return
        
        if not message.attachments[0].filename.endswith(('.png', '.jpeg', '.gif')):

            await self.__uncorrectImageRespond(message)
            return
                
        await self.__correctMessageRespond(message, listOfPotansialNick)
        return

    async def __correctMessageRespond(self, message: discord.Message, potentialUserNames: list[str]):

        image = await _converAttachmentToImage(message.attachments[0])
        if image is None:
            await self.__uncorrectScript(message)
            return

        profileParser = MainProfileParser(image, self.__dataCog.clanLinks.keys())
        realName = None
        
        for userName in potentialUserNames:

            if ratio(userName, profileParser.userName, processor = wordSimplificationEng) > self.MINIMUM_PART_MATCH:
                realName = userName
                break

        if realName is None:
            await self.__uncorrectScript(message)
            return
        
        if profileParser.clanName is None:
            role = self.bot.cogs['SWDataCog'].roleWithoutClan
        else:
            role = self.bot.cogs['SWDataCog'].clanLinks[profileParser.clanName]['role']
        
        await finishWithMember(message.author, f'[{"" if role is None else role.name}] {realName}', role, message)

    async def __unfindImageRespond(self, message: discord.Message, potentialUserNames: list[str]):

        await self.__createErrorThread(
            'Нет скрина',
            message,
            _MessageAfterProfileParse.UNFIND_IMAGE.value,
            None,
            None,
            True,
            _TempThreadWithData(_MessageAfterProfileParse.UNFIND_IMAGE, message, None, potentialUserNames)
        )

    async def __uncorrectImageRespond(self, message: discord.Message):
        await self.__createErrorThread(
            'Нечитабельный файл',
            message,
            _MessageAfterProfileParse.UNCORRECT_IMAGE.value,
            None,
            _MessageAfterProfileParse.UNCORRECT_IMAGE_REPORT.value.format( name = message.author),
            False
        )

    async def __uncorrectHeaderRespond(self, message: discord.Message):
        
        image = await _converAttachmentToImage(message.attachments[0])
        if image:
            profileImageParser = MainProfileParser(image, self.__dataCog.clanLinks.keys())

            if profileImageParser.userName:

                if profileImageParser.clanName is None:
                    role = self.bot.cogs['SWDataCog'].roleWithoutClan
                else:
                    role = self.bot.cogs['SWDataCog'].clanLinks[profileImageParser.clanName]['role']

                await self.__createErrorThread(
                    'Нет заголовка',
                    message,
                    _MessageAfterProfileParse.UNCORRECT_HEADER.value.format(name = profileImageParser.userName),
                    ProfileMessageWithoutHeaderView(nameFromImage = profileImageParser.userName, role = role, currentMessage = message),
                    None,
                    False
                )
                return
        
        await self.__uncorrectImageRespond(message)
        return

    async def __uncorrectMessageRespond(self, message: discord.Message):
        await replyAndAlarm(message, _MessageAfterProfileParse.UNCORRECT_MESSAGE.value, isDelete = True)

        try:
            await finishWithMember(currentMessage=message)
        except discord.HTTPException | discord.Forbidden:
            logging.info(f'::{self.CANT_DELETE_MESSAGE}')

    async def __uncorrectScript(self, message: discord.Message):
        await self.__createErrorThread(
            'Ошибка соотношения',
            message,
            _MessageAfterProfileParse.UNCORRECT_SCRIPT.value,
            None,
            _MessageAfterProfileParse.UNCORRECT_SCRIPT_REPORT.value.format(name = message.author),
            False
        )

    async def __createErrorThread(self, theadHeader: str, message: discord.Message, messageForUser: str, viewForUser: discord.ui.View | None, messageForModerator: str | None, isAddToTempTread: bool, data: _TempThreadWithData = None):

        try:

            tempThread: discord.Thread = await message.create_thread(name = theadHeader)

            if isAddToTempTread:
                data.currentThread = tempThread
                self.addThreadListener(tempThread.id, data)

            tempMessage = await tempThread.send(messageForUser, view = viewForUser)

            if viewForUser:
                viewForUser.thread = tempThread
                viewForUser.messageWithButton = tempMessage

        except discord.Forbidden:
            logging.info(f'::{self.CANT_SEND_TO_PROFILE_THREAD}')

        if self.bot.cogs['SWDataCog'].profileParseReportChannel and messageForModerator:

            try:
                await self.bot.cogs['SWDataCog'].profileParseReportChannel.send(messageForModerator)
            except discord.Forbidden:
                logging.info(f'::{self.CANT_SEND_TO_MODER_CHAT}')

    MIN_SYMBOLE_IN_NIKE = 3

    def __extractNameFromProfileMessage(self, messageHeader: str) -> list[str]:

        # Standart

        listOfPotansialNick = messageHeader.split()

        numberOfPotansialName = 0

        while numberOfPotansialName < len(listOfPotansialNick):

            if len(messageHeader[numberOfPotansialName]) > self.MIN_SYMBOLE_IN_NIKE or re.search(r'[А-Яа-я]', listOfPotansialNick[numberOfPotansialName]):

                listOfPotansialNick.pop(numberOfPotansialName)

            else:
                
                hashTagIndex = messageHeader[numberOfPotansialName].find('#')
                if hashTagIndex != -1:
                    messageHeader[numberOfPotansialName] = messageHeader[numberOfPotansialName][:hashTagIndex]

                numberOfPotansialName += 1

        return listOfPotansialNick

    #################################
    #                               #
    #        Resource Parse         #
    #                               #
    #################################

    THEAD_HEADER = 'Ресурсы?'
    NEED_RESOURCE_QUANTITY = 2

    async def __resourceParser(self, message: discord.Message):

        rank = attemptExtractRank(message.content)

        if rank is None and len(message.attachments) == 0:
            await finishWithMember(currentMessage = message)
            return

        threadForUser: discord.Thread | None = None
        attachments: list[discord.Attachment] = message.attachments
        try:

            attachments, threadForUser = await self.__getAttaempt(message)
            if len(attachments) == 0:
                return

            if rank is None:
                if threadForUser is None: threadForUser = await message.create_thread(name = self.THEAD_HEADER)
                rank = await self.__waitForRank(threadForUser)

            resources, quantityResource, isOtherName = await self.__getResource(
                self.NEED_RESOURCE_QUANTITY,
                rank,
                extractNameWithouClan(message.author.name) if message.author.nick is None else extractNameWithouClan(message.author.nick),
                attachments
            )

            clanChannel = None
            for links in self.__dataCog.clanLinks.values():
                if links['role'] in message.author.roles:
                    clanChannel = links['alert_channel']
                    break

            infoAboutResource = ''
            for resourceObj, value in resources.items():
                needQuantity = resourceObj.getQuantityOnRank(rank)
                infoAboutResource += f'\n{":white_check_mark:" if value >= needQuantity else ":x:"} {resourceObj}: {value}/{needQuantity}'

            if quantityResource < self.NEED_RESOURCE_QUANTITY:
                
                
                if threadForUser is None: threadForUser = await message.create_thread(name = self.THEAD_HEADER)
                
                tempView = ResourceParserQuestion(currentMessage=message, currentThread=threadForUser, rank=rank, attachment=attachments, clanChannel=clanChannel, isNameWaringn=isOtherName, infoAboutResource=infoAboutResource)
                messageWithButton = await threadForUser.send(
                    _MessageAfterResourseParse.NEED_MORE_RESOURCE.value.format( resource = infoAboutResource),
                    view = tempView                    
                )
                tempView.messageWithButton = messageWithButton
            else:
                if threadForUser is None: threadForUser = await message.create_thread(name = self.THEAD_HEADER)
                messageForReport = puckReportMessage(message, isOtherName, rank, infoAboutResource)
                await sendRespondAndReport(message, threadForUser, attachments, clanChannel, _MessageAfterResourseParse.CORRECT_ALL.value, messageForReport)

        except discord.HTTPException:
            logging.info(f'::{self.CANT_SEND_TO_PROFILE_CHANNEL}')
        except asyncio.TimeoutError:
            if threadForUser:
                await threadForUser.send( _MessageAfterResourseParse.TIMEOUT_RESPOND.value )
        except Exception as e:
            logging.info(str(e))
            await replyAndAlarm(message, _MessageAfterResourseParse.UNCORRECT_SCRIPT.value, _MessageAfterResourseParse.UNCORRECT_SCRIPT_REPORT.value.format(member = message.author, channel = message.channel), True)

    async def __getAttaempt(self, message: discord.Message):
        attachments = message.attachments
        threadForUser = None

        if len(attachments) == 0:
            threadForUser = await message.create_thread(name = self.THEAD_HEADER)
            attachments = await self.__waitForImage(threadForUser)
        
        if not any((a.filename.endswith(('.png', '.jpeg', '.gif')) for a in attachments)):
            if threadForUser is None: threadForUser = await message.create_thread(name = self.THEAD_HEADER)

            await threadForUser.send(_MessageAfterResourseParse.UNCORRECT_IMAGE.value)
            await self.__dataCog.profileParseReportChannel.send(_MessageAfterResourseParse.UNCORRECT_IMAGE_REPORT.value.format(member = message.author, channel = message.channel))
            return (attachments, threadForUser)
        
        return (attachments, threadForUser)

    async def __waitForImage(self, thread: discord.Thread):
        await thread.send(_MessageAfterResourseParse.MISSING_IMAGE.value)

        def check(potantialMessage: discord.Message):
            return len(potantialMessage.attachments) > 0 and potantialMessage.channel == thread

        mes = await self.bot.wait_for('message', timeout = TIMEOUT_BEFORE_DELETE, check=check)
        return mes.attachments

    async def __waitForRank(self, thread: discord.Thread):
        await thread.send(_MessageAfterResourseParse.MISSING_RANK.value)

        def check(potantialMessage: discord.Message):
            return not (attemptExtractRank(potantialMessage.content) is None)
        
        mes = await self.bot.wait_for('message', timeout = TIMEOUT_BEFORE_DELETE, check = check)
        return attemptExtractRank(mes.content)

    async def __getResource(self, howMuchNeed: int, rank: int, authorName: str, attachments: list[discord.Attachment]):
        resource = {}
        isOtherName = False
        quantityNow = 0

        for attachment in attachments:
            if attachment.filename.endswith(('.png', '.jpeg', '.gif')):
                image = await _converAttachmentToImage(attachment)
                resourceParser = ResourceProfileParser(image, rank)
                resource |= resourceParser.resource
                isOtherName = isOtherName or ratio(resourceParser.userName, authorName, processor = wordSimplificationEng) < self.MINIMUM_PART_MATCH
                quantityNow += resourceParser.enoughQuantityResource
                if quantityNow >= howMuchNeed:
                    return (resource, quantityNow, isOtherName)
        
        return (resource, quantityNow, isOtherName)

    #################################
    #                               #
    #      Temp Thread Handler      #
    #                               #
    #################################

    async def __extraThreadHandler(self, message: discord.Message, data: _TempThreadWithData) -> bool:

        if data.code in _MessageAfterProfileParse:
            
            if data.code == _MessageAfterProfileParse.UNFIND_IMAGE:
                return await self.__handleAfterMissImage(message, data)
            
            if data.code == _MessageAfterProfileParse.UNCORRECT_HEADER:
                return await self.__handelAfterMissHeader(message, data)
                
        

        return False
    
    async def __handleAfterMissImage(self, newMessage: discord.Message, data: _TempThreadWithData):

        if newMessage.author.id != data.currentMessage.author.id:
            return True

        if len(newMessage.attachments) == 0:

            await replyAndAlarm(newMessage, _MessageAfterProfileParse.UNFIND_IMAGE.value)
            return True
        
        image = await _converAttachmentToImage(newMessage.attachments[0])
        profileParser = MainProfileParser(image, self.__dataCog.clanLinks.keys())

        if profileParser.userName is None:

            await replyAndAlarm(newMessage, _MessageAfterProfileParse.UNCORRECT_SCRIPT.value, _MessageAfterProfileParse.UNCORRECT_SCRIPT_REPORT.format(name = newMessage.author))
            return False

        for name in data.listOfPotensialNames:

            if ratio(name, profileParser.userName, processor = wordSimplificationEng) > self.MINIMUM_PART_MATCH:

                if profileParser.clanName is None:
                    role = self.bot.cogs['SWDataCog'].roleWithoutClan
                else:
                    role = self.bot.cogs['SWDataCog'].clanLinks[profileParser.clanName]['role']
                    
                await finishWithMember(
                    newMessage.author,
                    f'[{"" if role is None else role.name}] {name}',
                    role, data.currentMessage,
                    data.currentThread
                )

                return False

        await replyAndAlarm(newMessage, _MessageAfterProfileParse.UNCORRECT_SCRIPT.value, _MessageAfterProfileParse.UNCORRECT_SCRIPT_REPORT.format(name = newMessage.author))
        return False

    async def __handelAfterMissHeader(self, newMessage: discord.Message, data: _TempThreadWithData):

        if newMessage.author.id != data.currentMessage.author.id:
            return True

        listOfName = self.__extractNameFromProfileMessage(newMessage.content)
        imageName: str = data.listOfPotensialNames[0]
        role: discord.Role | None = data.listOfPotensialNames[1]

        for name in listOfName:

            if ratio( name, imageName, processor = wordSimplificationEng ) > self.MINIMUM_PART_MATCH:

                await finishWithMember(
                    newMessage.author, 
                    f'[{"" if role is None else role.name}] {name}',
                    role,
                    data.currentMessage,
                    data.currentThread
                )
                return False
            
        await replyAndAlarm(newMessage, _MessageAfterProfileParse.UNCORRECT_SCRIPT.value, _MessageAfterProfileParse.UNCORRECT_SCRIPT_REPORT.format(name = newMessage.author))
        return True

    #################################
    #                               #
    #             UTIL              #
    #                               #
    #################################

    def addThreadListener(self, threadId: int, data: _TempThreadWithData):

        self.__threadForClarifications[threadId] = data

    def deleteThreadListener(self, thread: discord.Thread):

        if thread.id in self.__threadForClarifications:
            del self.__threadForClarifications[thread.id]

    def addResourceLinks(self, reportMessage: discord.Message, code: _MessageAfterProfileParse, currentMessage: discord.Message, thread: discord.Thread):
        self.__reportAndUserDataLink[reportMessage] = _TempThreadWithData(code ,currentMessage=currentMessage, currentTread=thread)

    def deleteReportLink(self, reportMessage: discord.Message):
        if reportMessage in self.__reportAndUserDataLink:
            del self.__reportAndUserDataLink[reportMessage]

ALL_COGS = [SWCog, SWUserCog]