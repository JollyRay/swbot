import logging
import discord
from discord.ext import commands
from discordPart.cog import parserSWChannel, arbitration, duviriAlert
from discordPart.cog.patrenCog import SWStandartCog

PREFIX = '♂'
swBot: commands.Bot = None

def setupBot():
    global swBot

    intents = discord.Intents(
        guilds = True,
        members = True,
        emojis = True,
        guild_messages = True,
        guild_reactions = True,
        message_content = True
    )

    swBot = commands.Bot(command_prefix = PREFIX, intents = intents)

    swBot.remove_command('help')
    swBot.add_command(help)

    parserSWChannel.setup(swBot, PREFIX)
    arbitration.setup(swBot, PREFIX)
    duviriAlert.setup(swBot, PREFIX)

    return swBot

@commands.command()
async def help(ctx: commands.Context):

    helpInfo: list[str] = list()
    
    for cog in swBot.cogs.values():
        
        if isinstance(cog, SWStandartCog):

            helpInfo.append(cog.getHelpMessage())
    
    logging.info(f'{ctx.author}:help')
    await ctx.send( '\n'.join(helpInfo) )