import json
import os
from datetime import datetime, timedelta

import pytz
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from timezonefinder import TimezoneFinder

from app.db import load_db, save_db
from app.keyboards import get_categories_keyboard, get_statistics_keyboard, get_reply_keyboard, CATEGORIES, MESSAGES, \
    geo_keybord
from logging_file import get_logger

logger = get_logger(__name__)  # Получаем логгер

tf = TimezoneFinder()


router = Router()


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

        print(config_items, next_item)

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

        elif next_item == "battery":

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
        db[user_id] = {
            "fio": None,
            "selected_options": [],
            "options_goal": {},
            "options_data": {}
        }
        save_db(db)
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
    db[user_id]["timezone"] = "Europe/Moscow"
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


# --- Обработчики внесения данных статистики ---
@router.callback_query(lambda c: c.data and c.data.startswith("entry:"))
async def callback_data_entry(callback: CallbackQuery, state: FSMContext) -> None:
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
    if category_key in ["wakeup_time", "abdomen", "tree"]:
        try:
            datetime.strptime(message.text, '%H:%M')
        except ValueError:
            await message.answer("Неверный формат времени. Введите время в формате Часы:Минуты (например, 07:00):")
            return
    elif category_key in ["abdomen", "tree"]:
        try:
            datetime.strptime(message.text, '%M:%S')
        except ValueError:
            await message.answer("Неверный формат времени. Введите время в формате Минуты:Секунды (например, 01:40):")
            return
    elif category_key == "battery":
        if not message.text.isdigit() or not (1 <= int(message.text) <= 10):
            await message.answer(MESSAGES["invalid_battery"])
            return
    elif category_key in ["steps", "pushups", "pullups", "squats", "abs"]:
        if not message.text.isdigit():
            await message.answer("Пожалуйста, введите корректное числовое значение. Попробуйте снова:")
            return
    db = load_db()
    user_entry = db.get(user_id)
    if user_entry is None:
        await message.answer(MESSAGES["user_not_found"])
        return

    FORMAT = "%Y-%m-%d"
    current_utc_time = datetime.now(pytz.utc)

    # Переводим в нужный часовой пояс
    user_time = current_utc_time.astimezone(pytz.timezone(user_entry["timezone"]))

    current_dt = user_time.strftime(FORMAT)

    now_dt = datetime.strptime(current_dt, FORMAT)
    print(now_dt)

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

    replaced = False
    if len(user_entry["options_data"][category_key]) > 0:
        last_dt = datetime.strptime(user_entry["options_data"][category_key][-1]["date_time"], FORMAT)
        if last_dt == now_dt:
            user_entry["options_data"][category_key][-1]["value"] = str(message.text)
            replaced = True
    if not replaced:
        user_entry["options_data"][category_key].append({
            "date_time": now_dt.strftime(FORMAT),
            "value": str(message.text)
        })

    db[user_id] = user_entry
    save_db(db)
    await message.answer(MESSAGES["value_saved"](category_key))
    await message.answer("Выберите другую категорию для внесения данных:",
                         reply_markup=get_statistics_keyboard(user_id, db))
    await state.clear()


# --- Обработчик reply‑клавиатуры ---
@router.message(F.text.in_(["Добавить запись", "Настройки", "Посмотреть статистику"]))
async def reply_keyboard_handler(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    db = load_db()
    if message.text == "Добавить запись":
        await message.answer(MESSAGES["enter_new_day"], reply_markup=get_statistics_keyboard(user_id, db))
    elif message.text == "Настройки":
        text = MESSAGES["settings_title"]
        await message.answer(text, reply_markup=get_categories_keyboard(user_id, db))
    elif message.text == "Посмотреть статистику":
        text = MESSAGES["get_link"](user_id)
        print(text)
        await message.answer(text, reply_markup=get_reply_keyboard(), parse_mode='HTML')
