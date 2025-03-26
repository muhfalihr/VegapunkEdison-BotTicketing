import asyncio
from edison import BotTicketing


def main():
    vegapunk = BotTicketing()
    asyncio.run(vegapunk.start_polling())

if __name__ == "__main__":
    main()