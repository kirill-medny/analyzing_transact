import json
import logging
import os
import re
from typing import Any, Dict, List

import pandas as pd

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
        person_transfer_pattern = re.compile(r"^[А-Я][а-я]+\s[А-Я]\.$")
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


# Основная Функция для "Сервисы"


def services() -> None:
    """
    Главная функция для расчета Инвесткопилки, простого поиска и поиска телефонных номеров для раздела "Сервисы".
    """
    # 1. Загрузка данных
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(project_root, "data", "operations.xlsx")
    df = pd.read_excel(data_path)

    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)
    df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)
    # Пример использования сервисов
    # Пример 1: Анализ выгодности категорий кешбэка
    year = 2021
    month = 11
    cashback_analysis = analyze_cashback_categories(df, year, month)
    print("Анализ выгодности категорий кешбэка:")
    print(cashback_analysis)

    # Пример 2: Расчет суммы для Инвесткопилки
    month_str: str = "2021-11"
    transactions = df.to_dict(orient="records")
    limit = 50
    investment_amount = investment_bank(month_str, transactions, limit)  # type: ignore[arg-type]
    print("\nСумма для Инвесткопилки:")
    print(investment_amount)

    # Пример 3: Простой поиск
    search_string = "Ozon"
    search_results = simple_search(search_string, df)
    print("\nРезультаты простого поиска:")
    print(search_results)

    # Пример 4: Поиск телефонных номеров
    phone_numbers = search_phone_numbers(df)
    print("\nТранзакции с телефонными номерами:")
    print(phone_numbers)

    # Пример 5: Поиск переводов физическим лицам
    person_transfers = search_person_transfers(df)
    print("\nПереводы физическим лицам:")
    print(person_transfers)
