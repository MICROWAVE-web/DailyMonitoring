import json
import os

DB_FILE = 'db.json'


def load_db() -> dict:
    """Загружает базу данных из файла JSON."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_db(db: dict) -> None:
    """Сохраняет базу данных в файл JSON."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
