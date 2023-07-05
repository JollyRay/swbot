import discord
from discord.ext import commands
from discordPart.cog import parserSWChannel, arbitration

PREFIX = '♂'

def setupBot():
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

    parserSWChannel.setup(swBot, PREFIX)
    arbitration.setup(swBot, PREFIX)

    return swBot