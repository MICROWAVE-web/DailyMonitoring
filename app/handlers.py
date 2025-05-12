import re
from datetime import datetime, timedelta
from itertools import count

import pytz
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestUsers, \
    InlineKeyboardMarkup, InlineKeyboardButton
from timezonefinder import TimezoneFinder

from app.db import load_db, save_db
from app.keyboards import get_categories_keyboard, get_statistics_keyboard, get_reply_keyboard, CATEGORIES, MESSAGES, \
    geo_keybord, get_buddies_keyboard
from app.tasks import schedule_custom_reminder, schedule_fixed_reminder
from logging_file import get_logger

logger = get_logger(__name__)

tf = TimezoneFinder()

router = Router()

FORMAT = "%Y-%m-%d"

bool_measures = ["water", "coordinate", "plank", "pray"]


# FSM-состояния для настройки параметров
class ConfigState(StatesGroup):
    fio = State()  # ввод ФИО
    wakeup_time = State()  # настройка времени подъёма
    steps = State()  # настройка нормы шагов
    pushups = State()  # настройка отжиманий
    pullups = State()  # настройка подтягиваний
    squats = State()  # настройка приседаний
    abs = State()  # настройка пресса
    abdomen = State()  # настройка Лада живота
    tree = State()  # настройка Дерева Жизни

    falconbreath = State()
    swimming = State()
    water = State()
    intention = State()
    note = State()

    breathholding = State()

    bars = State()


# FSM-состояния для внесения данных в статистику
class DataEntryState(StatesGroup):
    waiting_for_value = State()


def is_number(text: str) -> bool:
    return text.isdigit()


async def get_next_option_to_set(message: Message, state: FSMContext):
    data = await state.get_data()
    config_items = data.get("config_items", [])
    if len(config_items) > 0:
        next_item = config_items.pop(0)

        await state.update_data(config_items=config_items)
        if next_item == "wakeup_time":
            await message.answer(MESSAGES["enter_wakeup"])
            await state.set_state(ConfigState.wakeup_time)
        elif next_item == "steps":
            await message.answer(MESSAGES["enter_steps"])
            await state.set_state(ConfigState.steps)
        elif next_item == "pushups":
            await message.answer(MESSAGES["enter_pushups"])
            await state.set_state(ConfigState.pushups)
        elif next_item == "pullups":
            await message.answer(MESSAGES["enter_pullups"])
            await state.set_state(ConfigState.pullups)
        elif next_item == "squats":
            await message.answer(MESSAGES["enter_squats"])
            await state.set_state(ConfigState.squats)
        elif next_item == "abs":
            await message.answer(MESSAGES["enter_abs"])
            await state.set_state(ConfigState.abs)
        elif next_item == "abdomen":
            await message.answer(MESSAGES["enter_abdomen"])
            await state.set_state(ConfigState.abdomen)
        elif next_item == "tree":
            await message.answer(MESSAGES["enter_tree"])
            await state.set_state(ConfigState.tree)

        elif next_item == "falconbreath":
            await message.answer(MESSAGES["enter_falconbreath"])
            await state.set_state(ConfigState.falconbreath)

        elif next_item == "swimming":
            await message.answer(MESSAGES["enter_swimming"])
            await state.set_state(ConfigState.swimming)

        elif next_item == "breathholding":
            await message.answer(MESSAGES["enter_breathholding"])
            await state.set_state(ConfigState.breathholding)

        elif next_item == "bars":
            await message.answer(MESSAGES["enter_bars"])
            await state.set_state(ConfigState.bars)

        # elif next_item == "water":
        #     await message.answer(MESSAGES["enter_water"])
        #     await state.set_state(ConfigState.water)

        # elif next_item in ["battery", "water", "intention", "note"]:
        else:
            await get_next_option_to_set(message, state)
    else:
        await message.answer(MESSAGES["config_complete"], reply_markup=get_reply_keyboard())
        await state.clear()


# --- Обработчик команды /start и ввод ФИО ---
@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    db = load_db()
    if user_id not in db:

        default_timezone = "Europe/Moscow"
        db[user_id] = {
            "fio": None,
            "selected_options": [],
            "options_goal": {},
            "options_data": {},
            "timezone": default_timezone,
            "buddies": {},
            "buddies_remind": "00:00"
        }
        save_db(db)
        await schedule_fixed_reminder(user_id, default_timezone, 21)
        await schedule_fixed_reminder(user_id, default_timezone, 23)

        await message.answer(MESSAGES["start"])
        await state.set_state(ConfigState.fio)
    else:
        await message.answer(MESSAGES["welcome_back"], reply_markup=get_reply_keyboard())


@router.message(ConfigState.fio)
async def process_fio(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    fio = message.text.strip()
    db = load_db()
    db[user_id]["fio"] = fio
    save_db(db)
    text = MESSAGES["get_location"]

    await message.answer(text, reply_markup=geo_keybord())
    await state.clear()


# Хэндлер для обработки геолокации
@router.message(F.location)
async def handle_location(message: Message):
    user_id = str(message.from_user.id)
    latitude = message.location.latitude
    longitude = message.location.longitude

    # Определяем часовой пояс
    timezone_str = tf.timezone_at(lng=longitude, lat=latitude)
    if not timezone_str:
        await message.answer("Не удалось определить часовой пояс 😢")
        return

    # Конвертируем текущее время в часовой пояс пользователя
    user_timezone = pytz.timezone(timezone_str)
    user_time = message.date.astimezone(user_timezone)

    await message.answer(
        f"🌍 Ваш часовой пояс: {timezone_str}\n🕒 Локальное время: {user_time.strftime('%Y-%m-%d %H:%M:%S')}")

    db = load_db()
    db[user_id]["timezone"] = timezone_str
    fio = db[user_id]["fio"]
    save_db(db)

    await schedule_fixed_reminder(user_id, timezone_str, 21)
    await schedule_fixed_reminder(user_id, timezone_str, 23)

    if db[user_id].get("buddies_remind"):
        await schedule_custom_reminder(user_id, db[user_id]["buddies_remind"], timezone_str)

    text = MESSAGES["welcome"](fio)

    await message.answer(text, reply_markup=get_categories_keyboard(user_id, db))


@router.message(F.text.in_(["Позже"]))
async def later_handle_location(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    db = load_db()
    timezone_str = db[user_id]["timezone"]
    fio = db[user_id]["fio"]

    # Конвертируем текущее время в часовой пояс пользователя
    user_timezone = pytz.timezone(timezone_str)
    user_time = message.date.astimezone(user_timezone)

    await message.answer(
        f"🌍 Ваш часовой пояс: {timezone_str}\n🕒 Локальное время: {user_time.strftime('%Y-%m-%d %H:%M:%S')}")

    text = MESSAGES["welcome"](fio)

    await message.answer(text, reply_markup=get_categories_keyboard(user_id, db))


# --- Обработчик переключения выбранного параметра ---
@router.callback_query(lambda c: c.data and c.data.startswith("toggle:"))
async def callback_toggle_category(callback: CallbackQuery) -> None:
    user_id = str(callback.from_user.id)
    option_key = callback.data.split(":")[1]
    db = load_db()
    user_entry = db.get(user_id, {})
    selected = user_entry.get("selected_options", [])
    if option_key in selected:
        selected.remove(option_key)
    else:
        selected.append(option_key)
    user_entry["selected_options"] = selected
    db[user_id] = user_entry
    save_db(db)
    await callback.message.edit_reply_markup(reply_markup=get_categories_keyboard(user_id, db))
    await callback.answer()


# --- Обработчик завершения выбора параметров и переход к настройке норм ---
@router.callback_query(lambda c: c.data == "done")
async def callback_done(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = str(callback.from_user.id)
    db = load_db()
    selected = db[user_id].get("selected_options", [])
    if not selected:
        await callback.answer(MESSAGES["no_category_selected"], show_alert=True)
        return
    # Сохраняем выбранные опции для последовательной настройки норм
    await state.update_data(config_items=selected.copy())

    await get_next_option_to_set(callback.message, state)


# --- Обработчики настройки норм для каждого параметра ---
@router.message(ConfigState.wakeup_time)
async def process_wakeup_time(message: Message, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text, '%H:%M')
    except ValueError:
        await message.answer(MESSAGES["invalid_time"])
        return
    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["wakeup_time"] = message.text
    save_db(db)

    await get_next_option_to_set(message, state)


@router.message(ConfigState.steps)
async def process_steps(message: Message, state: FSMContext) -> None:
    if not is_number(message.text):
        await message.answer(MESSAGES["invalid_number"])
        return
    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["steps"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.pushups)
async def process_pushups(message: Message, state: FSMContext) -> None:
    if not is_number(message.text):
        await message.answer("Пожалуйста, введите корректное числовое значение для отжиманий.")
        return
    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["pushups"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.pullups)
async def process_pullups(message: Message, state: FSMContext) -> None:
    if not is_number(message.text):
        await message.answer("Пожалуйста, введите корректное числовое значение для подтягиваний.")
        return
    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["pullups"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.squats)
async def process_squats(message: Message, state: FSMContext) -> None:
    if not is_number(message.text):
        await message.answer("Пожалуйста, введите корректное числовое значение для приседаний.")
        return
    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["squats"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.abs)
async def process_abs(message: Message, state: FSMContext) -> None:
    if not is_number(message.text):
        await message.answer("Пожалуйста, введите корректное числовое значение для пресса.")
        return
    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["abs"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.abdomen)
async def process_abdomen(message: Message, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text, '%M:%S')
    except ValueError:
        await message.answer("Неверный формат времени. Введите время в формате Минуты:Секунды (например, 01:40):")
        return

    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["abdomen"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.tree)
async def process_tree(message: Message, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text, '%M:%S')
    except ValueError:
        await message.answer("Неверный формат времени. Введите время в формате Минуты:Секунды (например, 01:40):")
        return

    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["tree"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.falconbreath)
async def process_falconbreath(message: Message, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text, '%M:%S')
    except ValueError:
        await message.answer("Неверный формат времени. Введите время в формате Минуты:Секунды (например, 01:40):")
        return

    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["falconbreath"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.swimming)
async def process_swimming(message: Message, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text, '%M:%S')
    except ValueError:
        await message.answer("Неверный формат времени. Введите время в формате Минуты:Секунды (например, 01:40):")
        return

    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["swimming"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.swimming)
async def process_swimming(message: Message, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text, '%M:%S')
    except ValueError:
        await message.answer("Неверный формат времени. Введите время в формате Минуты:Секунды (например, 01:40):")
        return

    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["swimming"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.breathholding)
async def process_abs(message: Message, state: FSMContext) -> None:
    if not is_number(message.text):
        await message.answer("Пожалуйста, введите корректное числовое значение для пресса.")
        return
    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["breathholding"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


@router.message(ConfigState.bars)
async def process_abs(message: Message, state: FSMContext) -> None:
    if not is_number(message.text):
        await message.answer("Пожалуйста, введите корректное числовое значение для брусьев.")
        return
    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["bars"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)


"""@router.message(ConfigState.water)
async def process_water(message: Message, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text, '%M:%S')
    except ValueError:
        await message.answer(
            "Неверный формат времени. Введите время в формате Минуты:Секунды (например, 01:40):")
        return

    user_id = str(message.from_user.id)
    db = load_db()
    db[user_id]["options_goal"]["water"] = message.text
    save_db(db)
    await get_next_option_to_set(message, state)"""


# --- Обработчики внесения данных статистики ---
@router.callback_query(lambda c: c.data and c.data.startswith("entry:"))
async def callback_data_entry(callback: CallbackQuery, state: FSMContext) -> None:

    data = await state.get_data()
    print(data.get("yesterday"))

    category_key = callback.data.split(":")[1]
    await state.update_data(entry_category=category_key)
    category_name = CATEGORIES.get(category_key, category_key)
    await callback.message.answer(MESSAGES["enter_value"](category_name))
    await state.set_state(DataEntryState.waiting_for_value)
    await callback.answer()


@router.message(DataEntryState.waiting_for_value)
async def process_data_entry(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    data = await state.get_data()
    category_key = data.get("entry_category")
    yesterday = data.get("yesterday")

    if category_key in ["wakeup_time", "swimming"]:
        try:
            datetime.strptime(message.text, '%H:%M')
        except ValueError:
            await message.answer("Неверный формат времени. Введите время в формате Часы:Минуты (например, 07:00):")
            return
    elif category_key in ["abdomen", "tree", "falconbreath"]:
        try:
            datetime.strptime(message.text, '%M:%S')
        except ValueError:
            await message.answer("Неверный формат времени. Введите время в формате Минуты:Секунды (например, 01:40):")
            return
    elif category_key == "battery":
        if not message.text.isdigit() or not (1 <= int(message.text) <= 10):
            await message.answer(MESSAGES["invalid_battery"])
            return
    elif category_key in ["steps", "pushups", "pullups", "squats", "abs", "bars", "breathholding"]:
        if not message.text.isdigit():
            await message.answer("Пожалуйста, введите корректное числовое значение. Попробуйте снова:")
            return
    elif category_key in bool_measures:
        if not message.text.strip().lower() in ["ага", "да", "конечно", "нет", "не", "неа"]:
            await message.answer("Пожалуйста, введите корректное значение (Да/Нет). Попробуйте снова:")
            return
    db = load_db()
    user_entry = db.get(user_id)
    if user_entry is None:
        await message.answer(MESSAGES["user_not_found"])
        return

    current_utc_time = datetime.now(pytz.utc)

    # Переводим в нужный часовой пояс
    user_time = current_utc_time.astimezone(pytz.timezone(user_entry["timezone"]))

    if yesterday:
        user_time -= timedelta(days=1)

    current_dt = user_time.strftime(FORMAT)

    now_dt = datetime.strptime(current_dt, FORMAT)

    if category_key not in user_entry["options_data"]:
        user_entry["options_data"][category_key] = []

    # Если человек пропустил несколько дней, то заполняем данные нулями
    if len(user_entry["options_data"][category_key]) > 0:
        last_dt = datetime.strptime(user_entry["options_data"][category_key][-1]["date_time"], FORMAT)
        diff = now_dt - last_dt
        while diff > timedelta(days=1):
            user_entry["options_data"][category_key].append({
                "date_time": last_dt.strftime(FORMAT),
                "value": "0"
            })
            last_dt += timedelta(days=1)
            diff = now_dt - last_dt

    value_to_save = str(message.text)

    if category_key in bool_measures:
        if value_to_save.lower() in ["ага", "да", "конечно"]:
            value_to_save = "1"
        else:
            value_to_save = "0"

    replaced = False
    if len(user_entry["options_data"][category_key]) > 0:
        last_dt = datetime.strptime(user_entry["options_data"][category_key][-1]["date_time"], FORMAT)
        if last_dt == now_dt:
            user_entry["options_data"][category_key][-1]["value"] = value_to_save
            replaced = True
    if not replaced:
        user_entry["options_data"][category_key].append({
            "date_time": now_dt.strftime(FORMAT),
            "value": value_to_save
        })

    db[user_id] = user_entry
    save_db(db)
    await message.answer(MESSAGES["value_saved"](category_key))
    await message.answer("Выберите другую категорию для внесения данных:",
                         reply_markup=get_statistics_keyboard(user_id, yesterday=yesterday))

    await state.clear()
    if yesterday:
        await state.update_data(yesterday=yesterday)

def get_daily_report(user_id):
    daily_report_elements = []

    db = load_db()
    timezone_str = db[user_id]["timezone"]

    today_date_object = datetime.now(pytz.utc).astimezone(pytz.timezone(timezone_str)).date()
    today = str(today_date_object.today())

    min_date = None
    selected_options = db.get(user_id, {}).get("selected_options", [])
    for key in selected_options:
        records = db.get(user_id, {}).get("options_data", {}).get(key, [])
        goal = db.get(user_id, {}).get("options_goal", {}).get(key, "0")
        if not records:
            continue
        min_date_in_records = min([datetime.strptime(rec["date_time"], FORMAT).date() for rec in records])
        if min_date is None:
            min_date = min_date_in_records
        min_date = min(min_date, min_date_in_records)

        record = [rec for rec in records if rec["date_time"].startswith(today)]
        if len(record) > 0:
            record = record[0]
            name = CATEGORIES.get(key, key)
            record_val = f": {record['value']}"
            if key in bool_measures:
                record_val = ''

            if key not in ["intention", "note"]:
                if record['value'] >= goal:
                    record_val += ' ✅'

            if key == "battery":
                record_val += """
➖ 0 — «Еле живой»  
➖ 5 — «Держусь»  
➖ 10 — «Энергия через край!»"""

            daily_report_elements.append([key, f"{name}{record_val}\n"])

    daily_report_elements.sort(key=lambda elem: list(CATEGORIES.keys()).index(elem[0]))
    daily_report_text = "".join([elem[1] for elem in daily_report_elements])

    date_delta = (today_date_object - min_date).days
    daily_report_text = (f"🗓 Дата: {today.split('-')[-1]}.{today.split('-')[-2]} (день {date_delta})\n" +
                         daily_report_text)

    return daily_report_text


def get_goals(user_id):
    db = load_db()
    selected_options = db.get(user_id, {}).get("selected_options", [])
    goals_elems = []
    for key in selected_options:
        name = CATEGORIES.get(key, key)
        goal = db.get(user_id, {}).get("options_goal", {}).get(key)
        if goal:
            goals_elems.append([key, f"{name}: {goal}\n"])

    goals_elems.sort(key=lambda elem: list(CATEGORIES.keys()).index(elem[0]))
    goals_text = "".join([elem[1] for elem in goals_elems])

    return goals_text



reply_text = [
    "Добавить запись",
    "Настройки",
    "Посмотреть статистику",
    "Дневной отчёт",
    "Мои нормы",
    "Мои Бади",
    
    # Бади
    "Добавить 👤",
    "Выгнать 🚫",
    "Установить время напоминания 🕓",
    "Назад 🔙",
    "Забыл вчера внести данные",
]



@router.message(StateFilter("waiting_for_buddy_kick"))
async def handle_buddy_kick(message: Message, state: FSMContext):
    db = load_db()
    user_id = str(message.from_user.id)
    buddy_id = message.text.strip()

    if buddy_id.isdigit() and str(buddy_id) in db[user_id].get("buddies", {}):
        db[user_id]["buddies"].pop(str(buddy_id))
        save_db(db)
        await message.answer(f"Пользователь {buddy_id} удалён из бади")
    else:
        await message.answer("Некорректный выбор")
    await state.clear()



@router.message(StateFilter("waiting_for_remind_time"))
async def handle_remind_time(message: Message, state: FSMContext):
    db = load_db()
    user_id = str(message.from_user.id)
    new_time = message.text.strip()

    if not re.match(r"^\d{2}:\d{2}$", new_time):
        await message.answer(MESSAGES["invalid_time"])
        return

    db.get(user_id, {})["buddies_remind"] = new_time
    save_db(db)
    await schedule_custom_reminder(user_id, new_time, db[user_id]["timezone"])

    await message.answer(f"Время напоминания установлено: {new_time}")
    await state.clear()


@router.message(StateFilter("waiting_for_buddy_invite_method"))
async def choose_invite_method(message: Message, state: FSMContext):
    text = message.text
    if text == "Ввести ID вручную":
        await message.answer(MESSAGES["buddy_invite_id"])
        await state.set_state("waiting_for_buddy_id")
    elif message.contact or message.chat_shared or message.user_shared:
        await handle_buddy_contact(message, state)
    elif text == "Назад 🔙":
        await message.answer(MESSAGES["buddy_back"], reply_markup=get_reply_keyboard())
        await state.clear()
    else:
        await message.answer(MESSAGES["buddy_use_button"])



async def handle_buddy_contact(message: Message, state: FSMContext):
    db = load_db()
    user_id = str(message.from_user.id)

    buddy_object = None
    if message.contact:
        buddy_object = message.contact

    elif message.chat_shared:
        buddy_object = message.chat_shared

    elif message.user_shared:
        buddy_object = message.user_shared

    buddy_id = str(buddy_object.user_id)

    if buddy_id not in db.keys():
        await message.answer(MESSAGES["buddy_invalid_id_undefined"])

    if buddy_id == user_id:
        await message.answer(MESSAGES["buddy_self_error"])
        return

    db.setdefault(user_id, {}).setdefault("buddies", {})
    if buddy_id not in db[user_id]["buddies"].keys():
        db[user_id]["buddies"][buddy_id] = {
            "name": db[buddy_id]["fio"],
        }
        save_db(db)
        await message.answer(MESSAGES["buddy_added"](db[buddy_id]["fio"]), reply_markup=get_reply_keyboard(), parse_mode="HTML")
    else:
        await message.answer(MESSAGES["buddy_already_added"], reply_markup=get_reply_keyboard())

    await state.clear()



@router.message(StateFilter("waiting_for_buddy_id"))
async def handle_buddy_id_manual(message: Message, state: FSMContext):
    db = load_db()
    user_id = str(message.from_user.id)
    buddy_id = message.text.strip()

    if not buddy_id.isdigit():
        await message.answer(MESSAGES["buddy_invalid_id"])
        return

    if buddy_id not in db.keys():
        await message.answer(MESSAGES["buddy_invalid_id_undefined"])

    if buddy_id == user_id:
        await message.answer(MESSAGES["buddy_self_error"])
        return

    db.setdefault(user_id, {}).setdefault("buddies", [])
    if buddy_id not in db[user_id]["buddies"]:
        db[user_id]["buddies"][buddy_id] = {
            "name": db[buddy_id]["fio"],
        }
        await message.answer(MESSAGES["buddy_added"](buddy_id), reply_markup=get_reply_keyboard())
    else:
        await message.answer(MESSAGES["buddy_already_added"], reply_markup=get_reply_keyboard())

    await state.clear()


@router.callback_query(F.data.startswith("kick_buddy:"))
async def handle_kick_buddy_callback(callback: CallbackQuery):
    db = load_db()
    user_id = str(callback.from_user.id)
    buddy_id = callback.data.split(":")[1]

    if buddy_id not in db.get(user_id, {}).get("buddies", {}):
        await callback.answer("Этот пользователь уже не в вашем списке.", show_alert=True)
        return

    db[user_id]["buddies"].pop(buddy_id)
    save_db(db)

    buddy_name = db.get(str(buddy_id), {}).get("fio", str(buddy_id))
    await callback.message.edit_text(f"✅ {buddy_name} был удалён из ваших бади.")


# --- Обработчик reply‑клавиатуры ---
@router.message(F.text.in_(reply_text))
async def reply_keyboard_handler(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    db = load_db()
    if message.text == "Добавить запись":
        await state.update_data(yesterday=False)
        await message.answer(MESSAGES["enter_new_day"], reply_markup=get_statistics_keyboard(user_id))
    if message.text == "Забыл вчера внести данные":
        await state.update_data(yesterday=True)
        await message.answer(MESSAGES["enter_past_day"], reply_markup=get_statistics_keyboard(user_id, yesterday=True))
    elif message.text == "Настройки":
        text = MESSAGES["settings_title"]
        await message.answer(text, reply_markup=get_categories_keyboard(user_id, db))
    elif message.text == "Посмотреть статистику":
        text = MESSAGES["get_link"](user_id)
        await message.answer(text, reply_markup=get_reply_keyboard(), parse_mode='HTML')
    elif message.text == "Дневной отчёт":
        await message.answer(get_daily_report(user_id), parse_mode='HTML')
    elif message.text == "Мои нормы":
        await message.answer(get_goals(user_id), parse_mode='HTML')
    elif message.text == "Мои Бади":
        await message.answer("Что будем делать?\n\n"  + MESSAGES["chose_buddy_option"](db[user_id].setdefault("buddies", {})), reply_markup=get_buddies_keyboard(), parse_mode='HTML')

    elif message.text == "Добавить 👤":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Поделиться контактом 🤝", request_users=KeyboardButtonRequestUsers(
                        request_id=next(count(start=1, step=1)),
                        user_is_premium=False,
                        user_is_bot=False
                    ))],
                [KeyboardButton(text="Ввести ID вручную")],
                [KeyboardButton(text="Назад 🔙")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(MESSAGES["buddy_invite_choose_method"], reply_markup=kb)
        await state.set_state("waiting_for_buddy_invite_method")

    elif message.text == "Выгнать 🚫":
        db = load_db()
        user_id = str(message.from_user.id)
        buddies = db.get(user_id, {}).get("buddies", {}).keys()
        if not buddies:
            await message.answer(MESSAGES["empty"])
            return
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{db.get(str(b_id), {}).get('fio', 'Без имени')} — ({b_id})",
                    callback_data=f"kick_buddy:{b_id}"
                )]
                for b_id in buddies
            ]
        )
        await message.answer("Выберите, кого хотите выгнать из бади:", reply_markup=keyboard)


    elif message.text == "Установить время напоминания 🕓":
        await message.answer("Введите время напоминания в формате ЧЧ:ММ:")
        await state.set_state("waiting_for_remind_time")

    elif message.text == "Назад 🔙":
        await message.answer("Главное меню", reply_markup=get_reply_keyboard(), parse_mode='HTML')

