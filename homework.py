import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from telegram import Bot

from exceptions import HWParseError

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение {message} отправлено')
    except Exception as error:
        logging.error(f'Произошла ошибка: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к URL, возвращает json-файл."""
    params = {'from_date': current_timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Сайт не доступен, код ответа {response.status_code}')
        raise Exception(f'Сайт не доступен, код ответа{response.status_code}')
    try:
        response = response.json()
        logging.info(f'Получен ответ: {response}')
        return response
    except Exception as error:
        logging.error(f'Произошла ошибка: {error}')


def check_response(response):
    """Проверяет ответ API на корректность.
    Возвращает список домашних работ,
    доступный в ответе API по ключу 'homeworks'
    """
    if type(response) is not dict:
        logging.error(f'{type(response)} не является словарем')
        raise TypeError(f'{type(response)} не является словарем')
    try:
        homework = response.get('homeworks')[0]
    except Exception as error:
        logging.error(f'Произошла ошибка: {error}')
        raise HWParseError(f'Произошла ошибка: {error}')
    return homework


def check_tokens():
    """Проверяет доступность переменных окружения.
    Возвращает True, если они доступны.
    """
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def parse_status(homework):
    """Извлекает информацию о статусе домашней работы."""
    if 'homework_name' not in homework:
        logging.error('Ключ "homework_name" не найден в ответе')
        raise KeyError('Ключ "homework_name" не найден в ответе')
    if 'status' not in homework:
        logging.error('Ключ "status" не найден в ответе')
        raise Exception('Ключ "status" не найден в ответе')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logging.error('Статус домашней работы несуществует')
        raise KeyError('Статус домашней работы несуществует')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logging.critical(
            f'Переменные окружения недоступны:\n'
            f'{PRACTICUM_TOKEN}\n {TELEGRAM_TOKEN}\n {TELEGRAM_CHAT_ID}'
        )
        raise Exception('Переменные окружения недоступны')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date', current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            bot.send_message(TELEGRAM_CHAT_ID, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
