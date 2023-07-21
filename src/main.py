import logging
import os
from dotenv import load_dotenv
from discordPart import setupBot

if __name__ == '__main__':
    logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s:%(message)s')
    load_dotenv()
    swBot = setupBot()
    swBot.run(os.getenv('DISCORD_BOT_TOKEN'))