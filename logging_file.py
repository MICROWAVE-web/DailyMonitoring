# Настраиваем логирование
import logging

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] - %(message)s",
    level=logging.INFO,
)

# Отдельный логгер для Flask
flask_logger = logging.getLogger('werkzeug')
flask_logger.setLevel(logging.INFO)

# Создаём логгер для каждого модуля
def get_logger(name: str):
    return logging.getLogger(name)