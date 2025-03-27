import logging
import os
import time
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from pandas import DataFrame
from tinkoff.invest import AsyncClient, Client, InstrumentStatus
from tinkoff.invest.services import InstrumentsService

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv("../.env")
API_TOKEN = os.getenv("API_TOKEN")

# Функции для страницы "Главная"


def get_greeting(current_time: dt_time) -> str:
    """
    Определяет приветствие в зависимости от времени суток.
    """
    if 6 <= current_time.hour < 12:
        return "Доброе утро"
    elif 12 <= current_time.hour < 18:
        return "Добрый день"
    elif 18 <= current_time.hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def get_card_data(df: pd.DataFrame) -> list:
    """
    Получает данные по каждой карте: последние 4 цифры, общая сумма расходов, кешбэк.
    """
    card_data = []
    for card in df["Номер карты"].unique():
        card_df = df[df["Номер карты"] == card]
        total_spent = card_df["Сумма платежа"].sum()
        cashback = total_spent / 100
        card_data.append(
            {"last_digits": str(card), "total_spent": round(total_spent, 2), "cashback": round(cashback, 2)}
        )
    return card_data


def get_top_transactions(df: pd.DataFrame) -> list:
    """
    Получает топ-5 транзакций по сумме платежа.
    """
    # Сортируем по возрастанию, так как большие отрицательные числа - это большие расходы
    top_transactions = df.sort_values(by="Сумма платежа", ascending=True).head(
        5
    )  # True для фортировки отрицательных значений, False для положительных
    return [
        {
            "date": row["Дата операции"].strftime("%d.%m.%Y"),
            "amount": round(row["Сумма платежа"], 2),
            "category": row["Категория"],
            "description": row["Описание"],
        }
        for index, row in top_transactions.iterrows()
    ]


# Функции для страницы "Главная" и страницы "События"


def get_currency_rates(
    currencies: List[str], max_retries: int = 3, retry_delay: int = 5
) -> Dict[str, Optional[float]]:
    """
    Получает курсы валют с использованием API с обработкой ошибок и повторными попытками.
    """

    currency_data = {}
    for currency in currencies:
        if currency != "RUB":
            for attempt in range(max_retries):
                try:
                    response = requests.get("https://www.cbr-xml-daily.ru/daily_json.js")
                    response.raise_for_status()  # Поднимает HTTPError для плохих ответов (4xx или 5xx)
                    data = response.json()
                    currency_data[currency] = data["Valute"][currency]["Value"]
                    break  # Выход из цикла повторных попыток при успехе
                except requests.exceptions.RequestException as e:
                    print(f"Ошибка при получении курса {currency} (попытка {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        print(f"Повторная попытка через {retry_delay} секунд...")
                        time.sleep(retry_delay)
                    else:
                        print(f"Превышено максимальное количество попыток для {currency}.")
                        currency_data[currency] = None
                except KeyError as e:
                    print(f"Ошибка: Валюта {currency} не найдена в ответе API: {e}")
                    currency_data[currency] = None
                    break  # Нет смысла повторять, если валюта не найдена
                except Exception as e:
                    print(f"Ошибка при обработке данных для {currency}: {e}")
                    currency_data[currency] = None
                    break  # Нет смысла повторять, если есть проблема с обработкой данных
        else:
            continue

    return currency_data


async def get_stock_data(tickers: List[str]) -> List[Dict[str, Any]]:
    """
    Получает FIGI и последнюю цену для списка тикеров акций.

    Args:
        tickers (list): Список тикеров акций (например, ["AAPL", "AMZN"]).

    Returns:
        dict: Словарь, где ключ - тикер акции, а значение - словарь с FIGI и последней ценой.
               Возвращает None, если не удалось получить данные для тикера.
    """

    stock_data = []

    async with AsyncClient(API_TOKEN) as client:  # type: ignore[arg-type] # Используем AsyncClient для всего
        for ticker in tickers:
            try:
                # Сначала получаем FIGI
                with Client(API_TOKEN) as cl:  # type: ignore[arg-type]
                    instruments: InstrumentsService = cl.instruments
                    shares_df = DataFrame(
                        instruments.shares(instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE).instruments
                    )
                    figi = shares_df[shares_df["ticker"] == ticker]["figi"].iloc[0]

                # Затем получаем последнюю цену, используя AsyncClient
                last_price_response = await client.market_data.get_last_prices(figi=[figi])

                if last_price_response and last_price_response.last_prices:
                    last_price = (
                        last_price_response.last_prices[0].price.units
                        + last_price_response.last_prices[0].price.nano * 1e-9
                    )
                    stock_data.append({"stock": ticker, "price": last_price})  # Изменен формат

                else:
                    print(f"Нет данных о последней цене для {ticker}")
            except IndexError:
                print(f"Ошибка: Акция с тикером {ticker} не найдена.")
            except Exception as e:
                print(f"Ошибка при получении данных для {ticker}: {e}")
    return stock_data


def filter_transactions_by_month(df: pd.DataFrame, date: datetime) -> pd.DataFrame:
    """
    Фильтрует DataFrame транзакций по диапазону дат (от начала месяца до указанной даты).

    Args:
        df: DataFrame с транзакциями.
        date: Дата, до которой нужно фильтровать транзакции.

    Returns:
        Отфильтрованный DataFrame.
    """
    start_of_month = date.replace(day=1)
    return df[(df["Дата операции"] >= start_of_month) & (df["Дата операции"] <= date)]


# Функции для страницы "События"


def get_date_range(date: datetime, data_range: str = "M") -> tuple:
    """
    Определяет диапазон дат в зависимости от переданного параметра data_range.
    """
    if data_range == "W":
        # Неделя
        start_date = date - timedelta(days=date.weekday())
        end_date = start_date + timedelta(days=6)
    elif data_range == "M":
        # Месяц
        start_date = date.replace(day=1)
        end_date = date
    elif data_range == "Y":
        # Год
        start_date = date.replace(month=1, day=1)
        end_date = date
    elif data_range == "ALL":
        # Все данные
        start_date = datetime.min
        end_date = date
    else:
        raise ValueError("Неверный диапазон данных. Допустимые значения: W, M, Y, ALL")
    return start_date, end_date


def filter_transactions_by_date_range(df: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Фильтрует DataFrame транзакций по диапазону дат.
    """
    return df[(df["Дата операции"] >= start_date) & (df["Дата операции"] <= end_date)]


def get_expenses_data(df: pd.DataFrame) -> dict:
    """
    Получает данные о расходах: общая сумма, основные категории, переводы и наличные.
    """
    # Фильтруем только отрицательные суммы (расходы)
    expenses_df = df[df["Сумма платежа"] < 0].copy()  # .copy() чтобы избежать SettingWithCopyWarning

    # Общая сумма расходов
    total_amount = round(expenses_df["Сумма платежа"].sum())

    # Основные категории (исключаем "Наличные" и "Переводы")
    category_amounts = (
        expenses_df[~expenses_df["Категория"].isin(["Наличные", "Переводы"])]
        .groupby("Категория")["Сумма платежа"]
        .sum()
        .abs()
        .sort_values(ascending=False)
    )
    top_categories = category_amounts.head(7)
    other_amount = category_amounts[7:].sum()
    main = []
    for category, amount in top_categories.items():
        main.append({"category": category, "amount": round(amount)})
    main.append({"category": "Остальное", "amount": round(other_amount)})

    # Переводы и наличные
    transfers_and_cash_categories = ["Наличные", "Переводы"]
    transfers_and_cash = []

    for category in transfers_and_cash_categories:
        category_df = expenses_df[expenses_df["Категория"] == category]
        # amount = category_df['Сумма платежа'].sum().abs()  # Abs() for positive value
        amount = np.abs(category_df["Сумма платежа"].sum())
        transfers_and_cash.append({"category": category, "amount": round(amount)})

    return {"total_amount": total_amount, "main": main, "transfers_and_cash": transfers_and_cash}


def get_income_data(df: pd.DataFrame) -> dict:
    """
    Получает данные о доходах: общая сумма и основные категории.
    """
    # Фильтруем только положительные суммы (доходы)
    income_df = df[df["Сумма платежа"] > 0].copy()

    # Общая сумма доходов
    total_amount = round(income_df["Сумма платежа"].sum())

    # Основные категории доходов
    category_amounts = income_df.groupby("Категория")["Сумма платежа"].sum().sort_values(ascending=False)
    main = []
    for category, amount in category_amounts.items():
        main.append({"category": category, "amount": round(amount)})

    return {"total_amount": total_amount, "main": main}
