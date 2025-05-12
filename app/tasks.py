import asyncio
from datetime import datetime, time, timedelta
import pytz
from typing import Dict

from aiogram.types import InlineKeyboardMarkup

from app.db import load_db
from app.keyboards import CATEGORIES
from headers import bot
from logging_file import get_logger

logger = get_logger(__name__)
# Глобальный словарь для хранения активных напоминаний
reminder_tasks: Dict[str, asyncio.Task] = {}

REMIND_TIMES = ["21:00", "23:00"]


async def schedule_all_reminders():
    """
    Запускается при старте бота. Планирует все напоминания согласно данным в БД.
    """
    db = load_db()
    for user_id, user_data in db.items():
        timezone_str = user_data.get("timezone")
        if not timezone_str:
            continue

        # Планируем фиксированные напоминания
        await schedule_fixed_reminder(user_id, timezone_str, 21)
        await schedule_fixed_reminder(user_id, timezone_str, 23)

        buddies = user_data.get("buddies")
        remind_str = user_data.get("buddies_remind")

        if not buddies or not remind_str:
            continue
        await schedule_custom_reminder(user_id, remind_str, timezone_str)
        # await schedule_reminder(user_id, remind_str, timezone_str)

async def schedule_custom_reminder(user_id: str, remind_str: str, timezone_str: str):
    """
    Планирует пользовательское напоминание (buddies_remind).
    """
    await _schedule(user_id, remind_str, timezone_str, tag="buddy_remind")


async def schedule_fixed_reminder(user_id: str, timezone_str: str, hour: int):
    """
    Планирует фиксированное напоминание (в 21:00 и 23:00).
    """
    time_str = f"{hour:02d}:00"
    tag = f"fixed_{hour}"
    await _schedule(user_id, time_str, timezone_str, tag=tag)



async def _schedule(user_id: str, remind_str: str, timezone_str: str, tag: str):
    """
    Общая функция планирования напоминаний.
    """
    global reminder_tasks

    key = f'{user_id}_{tag}'
    old_task = reminder_tasks.get(key)
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
            _send_and_repeat(user_id, delay, hour, minute, timezone_str, tag)
        )
        reminder_tasks[key] = task
    except Exception as e:
        print(f"[!] Ошибка при планировании {tag} для {user_id}: {e}")



async def _send_and_repeat(user_id: str, delay: float, hour: int, minute: int, timezone_str: str, tag: str):
    await asyncio.sleep(delay)

    db = load_db()
    user_data = db.get(str(user_id))
    if not user_data:
        return

    try:
        text = ""

        if tag == "buddy_remind" and user_data.get("buddies"):

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
💪 Здравия , брат! 💪

Брат !
Твой бади не на связи. Может, интернет подвёл, что-то случилось, или он застрял в прокрастинации?

{buddy_text}
⚡️ Проверь ситуацию:
— Напиши ему, уточни как дела. Может, нужна помощь?
— Напомни: дисциплина — наш стержень, но брат брата учит, брат брата бережёт.
— Если всё ок — дай понять: команда ждет общего результата. Без слабины!

Не бросай своего. Мы здесь, чтобы поддерживать, но и держать удар.
Завтра будет жарче!

🔥 Держим круг!
            """


        elif tag.startswith("fixed_"):

            timezone_str = db[user_id]["timezone"]

            today = str(datetime.now(pytz.utc).astimezone(pytz.timezone(timezone_str)).date().today())

            missing_practice = ""
            selected_options = db.get(user_id, {}).get("selected_options", [])
            for key in selected_options:
                records = db.get(user_id, {}).get("options_data", {}).get(key, [])
                has_today = any(rec["date_time"].startswith(today) for rec in records)
                name = CATEGORIES.get(key, key)
                missing_practice += f"❌ {name}\n" if not has_today else ""

            if not missing_practice:
                return

            if tag.endswith("21"):
                text = f"❗ Не забудь записать свои показатели! Проверь свои практики и сделай запись ✍️\n\n{missing_practice}"
            elif tag.endswith("23"):
                text = f"🚨 Последний шанс успеть заполнить показатели! Проверь свои практики и сделай запись ✍️\n\n{missing_practice}"
        else:
            return

        if text:
            await bot.send_message(chat_id=int(user_id), text=text)

    except asyncio.CancelledError:
        return
    except Exception as e:
        print(f"[!] Ошибка отправки напоминания {tag} для {user_id}: {e}")

    # Рекурсивно перепланировать
    await _schedule(user_id, f"{hour:02d}:{minute:02d}", timezone_str, tag)
