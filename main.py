import asyncio
import logging
import threading

from app.handlers import router
from app.tasks import schedule_all_reminders
from flaskapp import flask_main
from headers import dp, bot

dp.include_router(router)

@dp.startup()
async def on_startup():
    await schedule_all_reminders()

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
