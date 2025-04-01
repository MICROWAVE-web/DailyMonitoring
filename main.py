import asyncio
import logging
import threading

from aiogram import Bot, Dispatcher
from decouple import config

from app.handlers import router
from flaskapp import flask_main

bot = Bot(token=config("BOT_TOKEN"))
dp = Dispatcher()
dp.include_router(router)


def main():
    try:
        # Run Flask in a separate thread (since it's blocking)
        flask_thread = threading.Thread(target=flask_main, daemon=True)
        flask_thread.start()

        asyncio.run(dp.start_polling(bot))
    except Exception as e:
        logging.exception(e)


if __name__ == "__main__":
    main()
