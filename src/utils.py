import json
import logging
import os
import re
from datetime import datetime, time, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

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
DEFAULT_REPORT_FILENAME = "report_{}.json"
REPORTS_DIRECTORY = "reports"

# Функции для страницы "Главная"


def get_greeting(current_time: time) -> str:
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


def get_currency_rates(currencies: List[str]) -> Dict[str, Optional[float]]:
    """
    Получает курсы валют с использованием API.
    """

    currency_data = {}
    for currency in currencies:
        if currency != "RUB":
            try:
                response = requests.get("https://www.cbr-xml-daily.ru/daily_json.js").json()
                currency_data[currency] = response["Valute"][currency]["Value"]  # Обрабат ответ API и извлекает курс
            except Exception as e:
                print(f"Ошибка при получении курса {currency}: {e}")
                currency_data[currency] = None  # Или другое значение по умолчанию
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


# Функции для раздела "Сервисы"


def analyze_cashback_categories(df: pd.DataFrame, year: int, month: int) -> str:
    """
    Анализирует, какие категории были наиболее выгодными для выбора в качестве
    категорий повышенного кешбэка в указанном месяце года.
    """
    try:
        logging.info(f"Анализ выгодности категорий кешбэка за {year}-{month}")

        # Фильтруем данные по году и месяцу, и только отрицательные суммы (расходы)
        filtered_data = df[
            (df["Дата операции"].dt.year == year) & (df["Дата операции"].dt.month == month) & (df["Сумма платежа"] < 0)
        ].copy()

        # Группируем по категориям и суммируем траты
        category_spending = filtered_data.groupby("Категория")["Сумма платежа"].sum().abs()

        # Рассчитываем потенциальный кешбэк (1%)
        category_cashback = category_spending * 0.01

        # Преобразуем в словарь и округляем значения
        cashback_analysis = category_cashback.round().to_dict()

        logging.info("Анализ выполнен успешно.")
        return json.dumps(cashback_analysis, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Рассчитывает сумму, которую удалось бы отложить в «Инвесткопилку».
    """
    try:
        logging.info(f"Расчет суммы для Инвесткопилки за {month} с лимитом {limit}")

        total_savings: float = sum(
            (limit - (transaction["Сумма операции"] % limit)) % limit
            for transaction in transactions
            if transaction["Дата операции"].strftime("%Y-%m") == month
        )

        logging.info(f"Сумма для Инвесткопилки: {total_savings}")
        return round(total_savings, 2)
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
        return 0.0


def simple_search(search_string: str, df: pd.DataFrame) -> str:
    """
    Ищет транзакции, содержащие запрос в описании или категории, и форматирует даты.
    """
    try:
        logging.info(f"Поиск транзакций по запросу: {search_string}")

        # 1. Форматируем столбец "Дата операции" в нужный формат
        df["Дата операции"] = df["Дата операции"].dt.strftime(
            "%d.%m.%Y %H:%M:%S"
        )  # Или другой формат, какой вам нужен
        df["Дата платежа"] = df["Дата платежа"].dt.strftime("%d.%m.%Y %H:%M:%S")

        # 2. Выполняем поиск
        search_results = df[
            df["Описание"].str.contains(search_string, case=False, na=False)
            | df["Категория"].str.contains(search_string, case=False, na=False)
        ]

        # 3. Преобразуем в JSON
        results = search_results.to_json(orient="records", force_ascii=False)

        logging.info(f"Найдено {len(search_results)} транзакций.")
        return results
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


def search_phone_numbers(df: pd.DataFrame) -> str:
    """
    Возвращает транзакции, содержащие в описании мобильные номера.
    """
    try:
        logging.info("Поиск транзакций с телефонными номерами.")

        # 1. Проверяем, не пустой ли DataFrame
        if df.empty:
            logging.info("Пустой DataFrame. Возвращаем пустой список.")
            return json.dumps([], indent=2, ensure_ascii=False)

        # 2. Выполняем поиск
        phone_number_pattern = re.compile(r"\+?\d{1,3}\s?\(?\d{3}\)?\s?\d{1,3}[-\s]?\d{2}[-\s]?\d{2}", re.IGNORECASE)
        phone_transactions = df[df["Описание"].str.contains(phone_number_pattern, regex=True, na=False)]

        # 3. Преобразуем в JSON
        results = phone_transactions.to_json(orient="records", force_ascii=False)
        logging.info(f"Найдено {len(phone_transactions)} транзакций с телефонными номерами.")
        return results
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


def search_person_transfers(df: pd.DataFrame) -> str:
    """
    Возвращает транзакции, которые относятся к переводам физлицам.
    """
    try:
        logging.info("Поиск переводов физическим лицам.")

        # 1. Проверяем, не пустой ли DataFrame
        if df.empty:
            logging.info("Пустой DataFrame. Возвращаем пустой список.")
            return json.dumps([], indent=2, ensure_ascii=False)

        # 2. Выполняем поиск
        person_transfer_pattern = re.compile(r"^Перевод\s[А-Я][а-я]+\s[А-Я]\.$")
        person_transfers = df[
            (df["Категория"] == "Переводы")
            & df["Описание"].str.contains(person_transfer_pattern, regex=True, na=False)
        ]

        # 3. Преобразуем в JSON
        results = person_transfers.to_json(orient="records", force_ascii=False)
        logging.info(f"Найдено {len(person_transfers)} переводов физическим лицам.")
        return results
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


# Функции для раздела "Отчеты"


def report_decorator(filename: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Декоратор для функций-отчетов, записывающий результат в файл.
    Результаты сохраняются в папку 'reports' в корневом каталоге проекта.
    Имя файла отчета включает имя функции, если имя файла не передано явно.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Union[Any, DataFrame]:
            try:
                result = func(*args, **kwargs)

                # Проверка директории reports
                if not os.path.exists(REPORTS_DIRECTORY):
                    os.makedirs(REPORTS_DIRECTORY)

                if filename:
                    filepath = os.path.join(REPORTS_DIRECTORY, filename)  # Объединение директории и названия
                else:
                    base_filename = DEFAULT_REPORT_FILENAME.format(
                        func.__name__, datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    )
                    filepath = os.path.join(REPORTS_DIRECTORY, base_filename)  # Объединение директории и названия

                with open(filepath, "w", encoding="utf-8") as f:
                    if isinstance(result, pd.DataFrame):  # Проверка, является ли результат DataFrame
                        json.dump(result.to_dict(orient="records"), f, indent=2, ensure_ascii=False, default=str)
                    else:
                        json.dump(
                            result, f, indent=2, ensure_ascii=False, default=str
                        )  # json.dump работает и со словарями, и со списками
                logging.info(f"Отчет {func.__name__} записан в файл: {filepath}")
                return result
            except Exception as e:
                logging.exception(f"Ошибка при выполнении отчета {func.__name__}: {e}")
                return pd.DataFrame(
                    {"error": [str(e)]}
                )  # Возвращает пустой фрейм данных, но сохраняет поток обработки

        return wrapper

    return decorator


@report_decorator()  # Использует имя файла по умолчанию
def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает траты по заданной категории за последние три месяца (от переданной даты).
    """
    try:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")  # YYYY-MM-DD
        report_date = datetime.strptime(date, "%Y-%m-%d")  # Убедитесь, что данные передаются в этом формате

        start_date = report_date - timedelta(days=3 * 30)  # Приблизительно 3 месяца

        filtered_transactions = transactions[
            (transactions["Дата операции"] >= start_date)
            & (transactions["Дата операции"] <= report_date)
            & (transactions["Категория"] == category)
            & (transactions["Сумма платежа"] < 0)  # Только расходы
        ]

        # Объединение суммы расходов по дате
        spending = (
            filtered_transactions.groupby("Дата операции")["Сумма платежа"].sum().abs()
        )  # .reset_index()   #abs для возврата положительного значения

        return spending.to_frame()  # преобразование рядов в DataFrame

    except Exception as e:
        logging.exception(f"Ошибка при формировании отчета spending_by_category: {e}")
        return pd.DataFrame({"error": [str(e)]})


@report_decorator(filename="weekday_spending_report.json")
def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает средние траты в каждый из дней недели за последние три месяца (от переданной даты).
    """
    try:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")  # YYYY-MM-DD
        report_date = datetime.strptime(date, "%Y-%m-%d")

        start_date = report_date - timedelta(days=3 * 30)

        filtered_transactions = transactions[
            (transactions["Дата операции"] >= start_date)
            & (transactions["Дата операции"] <= report_date)
            & (transactions["Сумма платежа"] < 0)  # Только расходы
        ].copy()  # Добавлена функция .copy(), чтобы избежать предупреждений

        # Выписка из будних дней
        filtered_transactions["День недели"] = filtered_transactions["Дата операции"].dt.day_name(locale="ru_RU")

        # Рассчитать средние расходы за будний день
        weekday_spending = (
            filtered_transactions.groupby("День недели")["Сумма платежа"].mean().abs()
        )  # Abs() чтобы вернуть положительное значение

        return weekday_spending.to_frame()
    except Exception as e:
        logging.exception(f"Ошибка при формировании отчета spending_by_weekday: {e}")
        return pd.DataFrame({"error": [str(e)]})


@report_decorator()
def spending_by_workday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Выводит средние траты в рабочий и в выходной день за последние три месяца (от переданной даты).
    """
    try:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")  # YYYY-MM-DD
        report_date = datetime.strptime(date, "%Y-%m-%d")

        start_date = report_date - timedelta(days=3 * 30)

        filtered_transactions = transactions[
            (transactions["Дата операции"] >= start_date)
            & (transactions["Дата операции"] <= report_date)
            & (transactions["Сумма платежа"] < 0)  # Только расходы
        ].copy()  # Добавлена функция .copy(), чтобы избежать предупреждений

        # Определите, рабочий это день или выходной
        filtered_transactions["Тип дня"] = filtered_transactions["Дата операции"].apply(
            lambda x: "Выходной" if x.weekday() >= 5 else "Рабочий"
        )

        # Рассчитайте средние расходы по типам дня
        workday_spending = (
            filtered_transactions.groupby("Тип дня")["Сумма платежа"].mean().abs()
        )  # Abs() чтобы вернуть положительное значение

        return workday_spending.to_frame()

    except Exception as e:
        logging.exception(f"Ошибка при формировании отчета spending_by_workday: {e}")
        return pd.DataFrame({"error": [str(e)]})
