import json
import os
import random
import string
from datetime import datetime, timedelta

from decouple import config
from flask import Flask, jsonify, render_template

from logging_file import get_logger

logger = get_logger(__name__)  # Получаем логгер


app = Flask(__name__)
# Словарь для хранения данных отчетов
reports = {}

# Путь к файлу JSON
DATA_FILE = 'db.json'

# Инициализация JSON-файла, если он не существует
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as file:
        json.dump({}, file)


def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)


# Генерация уникальной ссылки
def generate_unique_link():
    link = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    expiration_time = datetime.now() + timedelta(minutes=20)
    reports[link] = {"data": load_data(), "expires": expiration_time}
    return link


@app.route('/generate_report/<user_id>/', methods=['POST'])
def generate_report(user_id):
    request_data = load_data().get(user_id)
    if request_data is None:
        return jsonify({"error": "No data"}), 400
    link = generate_unique_link()
    reports[link]['data'] = request_data
    return jsonify({"link": f"/report/{link}"})


@app.route('/report/<user_id>', methods=['GET'])
def view_report(user_id):
    request_data = load_data().get(user_id)
    if request_data is None:
        return jsonify({"error": "No data"}), 400
    print(json.dumps(request_data))
    return render_template('report.html', data=json.dumps(request_data))


def flask_main():
    app.run(host="127.0.0.1", port=int(config("FLASK_PORT")), debug=False, use_reloader=False)  # <--- исправление
