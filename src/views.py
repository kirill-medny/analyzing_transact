import json
import logging
import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from src import utils

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv("../.env")
API_TOKEN = os.getenv("API_TOKEN")


async def main(datetime_str: str) -> str:
    """
    Главная функция для анализа транзакций и генерации JSON-ответа для главной страницы.
    """
    try:
        logging.info(f"Начало обработки данных для даты и времени: {datetime_str}")

        # 1. Загрузка данных
        file_path = os.path.join("..", "data", "operations.xlsx")
        df = pd.read_excel(file_path)

        # project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Поднимаемся на один уровень вверх от main.py
        # file_path = os.path.join(project_root, "operations.xlsx")
        # df = pd.read_excel(file_path)

        # 2. Преобразование столбцов с датами
        df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)
        df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)

        # 3. Входящая дата и время
        input_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        # 4. Фильтрация данных по дате
        filtered_df = utils.filter_transactions_by_month(df, input_datetime)

        # 5. Загрузка настроек пользователя
        with open("../user_settings.json", "r") as f:
            user_settings = json.load(f)
        user_currencies = user_settings["user_currencies"]
        user_stocks = user_settings["user_stocks"]

        # 6. Получение данных о валютах и акциях
        currency_rates = utils.get_currency_rates(user_currencies)
        stock_prices = await utils.get_stock_data(user_stocks)

        # 7. Генерация данных для главной страницы
        greeting = utils.get_greeting(input_datetime.time())
        card_data = utils.get_card_data(filtered_df)
        top_transactions = utils.get_top_transactions(filtered_df)

        # 8. Формирование JSON-ответа
        response_data = {
            "greeting": greeting,
            "cards": card_data,
            "top_transactions": top_transactions,
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
        }

        logging.info("Данные успешно обработаны.")
        return json.dumps(response_data, indent=2, ensure_ascii=False, default=str)  # ensure_ascii=False для кириллицы
    except FileNotFoundError:
        logging.error("Файл operations.xlsx не найден.")
        return json.dumps({"error": "Файл operations.xlsx не найден"}, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


async def events(datetime_str: str, data_range: str) -> str:
    """
    Главная функция для анализа транзакций и генерации JSON-ответа для страницы "События".
    """
    try:
        logging.info(f"Начало обработки данных для даты: {datetime_str}, диапазон: {data_range}")

        # 1. Загрузка данных
        df = pd.read_excel("../data/operations.xlsx")

        # 2. Преобразование столбцов с датами
        df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)
        df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)

        # 3. Входящая дата
        input_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        # 4. Определение диапазона данных
        start_date, end_date = utils.get_date_range(input_datetime, data_range)
        filtered_df = utils.filter_transactions_by_date_range(df, start_date, end_date)

        # 5. Загрузка настроек пользователя
        with open("../user_settings.json", "r") as f:
            user_settings = json.load(f)
        user_currencies = user_settings["user_currencies"]
        user_stocks = user_settings["user_stocks"]

        # 6. Получение данных о валютах и акциях
        currency_rates = utils.get_currency_rates(user_currencies)
        stock_prices = await utils.get_stock_data(user_stocks)

        # 7. Генерация данных для страницы "События"
        expenses_data = utils.get_expenses_data(filtered_df)
        income_data = utils.get_income_data(filtered_df)

        # 8. Формирование JSON-ответа
        response_data = {
            "expenses": expenses_data,
            "income": income_data,
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
        }

        logging.info("Данные успешно обработаны.")
        return json.dumps(response_data, indent=2, ensure_ascii=False)
    except FileNotFoundError:
        logging.error("Файл operations.xlsx не найден.")
        return json.dumps({"error": "Файл operations.xlsx не найден"}, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)
