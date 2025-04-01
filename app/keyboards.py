from datetime import datetime

import pytz
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from app.db import load_db
from logging_file import get_logger

logger = get_logger(__name__)  # Получаем логгер

# Список всех доступных параметров
CATEGORIES = {
    "wakeup_time": "🌅 Ранний подъём",
    "abdomen": "🌀 Лад живота",
    "tree": "🌳 Дерево Жизни",
    "steps": "🚶 Ходьба",
    "pushups": "💪 Отжимания",
    "pullups": "🤸 Подтягивания",
    "squats": "🏋️ Приседания",
    "abs": "🧘 Пресс",
    "battery": "🔋 Состояние",
}


def get_categories_keyboard(user_id: str, db: dict) -> InlineKeyboardMarkup:
    """
    Формирует inline‑клавиатуру для выбора параметров.
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    selected_options = db.get(user_id, {}).get("selected_options", [])
    for key, name in CATEGORIES.items():
        circle = "🟢" if key in selected_options else "⚪"
        text = f"{name} {circle}"
        button = InlineKeyboardButton(text=text, callback_data=f"toggle:{key}")
        kb.inline_keyboard.append([button])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Готово", callback_data="done")])
    return kb


def get_statistics_keyboard(user_id: str, db: dict) -> InlineKeyboardMarkup:
    """
    Формирует inline‑клавиатуру для внесения данных за текущий день.
    Если данные для выбранного параметра уже внесены (на текущую дату),
    перед названием параметра ставится галочка.
    """

    db = load_db()
    timezone_str = db[user_id]["timezone"]

    today = str(datetime.now(pytz.utc).astimezone(pytz.timezone(timezone_str)).date().today())

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    selected_options = db.get(user_id, {}).get("selected_options", [])
    for key in selected_options:
        records = db.get(user_id, {}).get("options_data", {}).get(key, [])
        has_today = any(rec["date_time"].startswith(today) for rec in records)
        name = CATEGORIES.get(key, key)
        text = f"✅ {name}" if has_today else name
        kb.inline_keyboard.append([InlineKeyboardButton(text=text, callback_data=f"entry:{key}")])
    return kb


def get_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Формирует reply‑клавиатуру с кнопками «Занести данные нового дня» и «Настройки».
    """
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить запись")],
            [KeyboardButton(text="Посмотреть статистику")],
            [KeyboardButton(text="Настройки")],
            [KeyboardButton(text="📍 Поменять локацию", request_location=True)]],

        resize_keyboard=True
    )
    return kb


def geo_keybord() -> ReplyKeyboardMarkup:
    """
    Формирует reply‑клавиатуру с кнопками «Отправить локацию».

    """
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить локацию", request_location=True)],
            [KeyboardButton(text="Позже")]
        ],
        resize_keyboard=True
    )
    return kb


# Сообщения бота
MESSAGES = {
    "start": "Добро пожаловать!\nПожалуйста, введите ваше ФИО:",
    "welcome_back": "И в новь добро пожаловать!\nРад вас видеть :)",
    "get_location": "Отправьте вашу геолокацию, чтобы определить часовой пояс!",
    "welcome": lambda fio: (
        f"Истинный путь\n\n"
        f"Привет, {fio}!\n"
        "Здесь вы сможете отслеживать свои повседневные практики.\n"
        "Сначала выберите параметры, которые хотите отслеживать:"
    ),
    "no_category_selected": "Пожалуйста, выберите хотя бы один параметр!",
    "settings_title": "Настройки\n\nВыберите параметры, которые хотите отслеживать:",
    "config_complete": "Настройка завершена.",
    "enter_value": lambda category_name: f"Введите значение для категории {category_name}:",
    "value_saved": lambda category_key: f"Значение для категории {CATEGORIES[category_key]} сохранено!",
    "enter_new_day": "Занесите данные нового дня:",
    "invalid_time": "Неверный формат времени. Введите время в формате ЧЧ:ММ (например, 07:00):",
    "invalid_battery": "Пожалуйста, введите число от 1 до 10 для категории Состояние (battery). Попробуйте снова:",
    "invalid_number": "Пожалуйста, введите корректное числовое значение. Попробуйте снова:",
    "user_not_found": "Ошибка: пользователь не найден в базе данных.",

    # Запросы на ввод значений для настроек
    "enter_wakeup": "Введите норму времени подъёма (например, 07:00):",
    "enter_steps": "Введите норму шагов (например, 4000):",
    "enter_pushups": "Введите норму количества отжиманий (например,  20):",
    "enter_pullups": "Введите норму количества подтягиваний (например, 10):",
    "enter_squats": "Введите норму количества приседаний (например, 30):",
    "enter_abs": "Введите норму количества повторов пресса (например, 15):",
    "enter_abdomen": "Введите норму для Лада живота (например, 01:30):",
    "enter_tree": "Введите норму для Дерева Жизни (например, 02:30):",

    "get_link": lambda user_id: f'📈 Вот ваша <a href="http://83.222.25.179:8015/report/{user_id}">Ссылка на статистику</a>',
}
