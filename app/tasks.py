import asyncio
from datetime import datetime, time, timedelta
import pytz
from typing import Dict

from app.db import load_db
from app.keyboards import CATEGORIES
from headers import bot
from logging_file import get_logger

logger = get_logger(__name__)
# Глобальный словарь для хранения активных напоминаний
reminder_tasks: Dict[str, asyncio.Task] = {}

async def schedule_all_reminders():
    """
    Запускается при старте бота. Планирует все напоминания согласно данным в БД.
    """
    db = load_db()
    for user_id, user_data in db.items():
        buddies = user_data.get("buddies")
        remind_str = user_data.get("buddies_remind")
        timezone_str = user_data.get("timezone")

        if not buddies or not remind_str or not timezone_str:
            continue

        await schedule_reminder(user_id, remind_str, timezone_str)


async def schedule_reminder(user_id: str, remind_str: str, timezone_str: str):
    """
    Создаёт или перезапускает напоминание для конкретного пользователя.
    """
    global reminder_tasks

    # Отменим предыдущее напоминание, если оно есть
    old_task = reminder_tasks.get(user_id)
    if old_task:
        old_task.cancel()

    try:
        hour, minute = map(int, remind_str.split(":"))
        user_tz = pytz.timezone(timezone_str)
        now = datetime.now(user_tz)
        target_time = user_tz.localize(datetime.combine(now.date(), time(hour, minute)))

        if target_time < now:
            target_time += timedelta(days=1)

        delay = (target_time - now).total_seconds()

        task = asyncio.create_task(
            send_reminder_and_repeat(user_id, delay, hour, minute, timezone_str)
        )
        reminder_tasks[user_id] = task
    except Exception as e:
        logger.exception(f"[!] Ошибка при планировании напоминания для {user_id}: {e}")


async def send_reminder_and_repeat(user_id: str, delay: float, hour: int, minute: int, timezone_str: str):
    """
    Отправляет напоминание и рекурсивно запускает его на следующий день.
    """
    try:
        await asyncio.sleep(delay)

        db = load_db()
        user_data = db.get(str(user_id))
        if not user_data or not user_data.get("buddies"):
            return

        #buddy_names = [
        #    b_info.get("name", str(b_id))
        #    for b_id, b_info in user_data["buddies"].items()
        # ]

        # Получаем поля, которые не заполнил buddy

        buddy_text = ""

        for b_key in user_data["buddies"].keys():
            b_info = db[b_key]

            buddy_timezone_str = b_info["timezone"]

            buddy_fio = f"👤 Бади: {b_info['fio']}"
            buddy_missing = ""


            today = str(datetime.now(pytz.utc).astimezone(pytz.timezone(buddy_timezone_str)).date().today())

            selected_options = db.get(user_id, {}).get("selected_options", [])
            for key in selected_options:
                records = db.get(user_id, {}).get("options_data", {}).get(key, [])
                has_today = any(rec["date_time"].startswith(today) for rec in records)
                name = CATEGORIES.get(key, key)

                buddy_missing += f"❌ {name}\n" if not has_today else ""

            if buddy_missing:
                buddy_text += f"{buddy_fio}\n{buddy_missing}\n"

        if not buddy_text:
            return

        text = f"""
💪 Тревога, брат! 💪

Эй, друг!
Твой бади не на связи. Может, интернет подвёл, что-то случилось, или он застрял в прокрастинации?

{buddy_text}
⚡️ Проверь ситуацию:
— Напиши ему, уточни как дела. Может, нужна помощь?
— Напомни: дисциплина — наш стержень, но брат брата учит, брат брата бережёт.
— Если всё ок — дай понять: команда ждет общего результата. Без слабины!

Не бросай своего. Мы здесь, чтобы поддерживать, но и держать удар.
Свяжись, разберись, и — вперёд. Завтра будет жарче!

🔥 Никаких отступлений. Только воля и действие.
        """

        await bot.send_message(chat_id=int(user_id), text=text)

    except asyncio.CancelledError:
        logger.info(f"[!] Напоминание для {user_id} было отменено")
        return
    except Exception as e:
        logger.exception(f"[!] Ошибка отправки напоминания для {user_id}: {e}")

    # Планируем на следующий день
    try:
        await schedule_reminder(user_id, f"{hour:02d}:{minute:02d}", timezone_str)
    except Exception as e:
        logger.exception(f"[!] Ошибка при повторном планировании напоминания для {user_id}: {e}")
