from Logger import Logger
from discord_bot import run_bot

if __name__ == "__main__":
    try:
        run_bot()
    except Exception as e:
        Logger.critical('Internal error occurred', e)
    finally:
        Logger.critical('Shutting down bot...')
