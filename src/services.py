import logging

import pandas as pd

from src import utils

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# file_path = os.path.join("..", "data", "operations.xlsx")
# df = pd.read_excel(file_path)


def services() -> None:
    # 1. Загрузка данных
    df = pd.read_excel("../data/operations.xlsx")
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)
    df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)
    # Пример использования сервисов
    # Пример 1: Анализ выгодности категорий кешбэка
    year = 2021
    month = 11
    cashback_analysis = utils.analyze_cashback_categories(df, year, month)
    print("Анализ выгодности категорий кешбэка:")
    print(cashback_analysis)

    # Пример 2: Расчет суммы для Инвесткопилки
    month_str: str = "2021-11"
    transactions = df.to_dict(orient="records")
    limit = 50
    investment_amount = utils.investment_bank(month_str, transactions, limit)  # type: ignore[arg-type]
    print("\nСумма для Инвесткопилки:")
    print(investment_amount)

    # Пример 3: Простой поиск
    search_string = "Ozon"
    search_results = utils.simple_search(search_string, df)
    print("\nРезультаты простого поиска:")
    print(search_results)

    # Пример 4: Поиск телефонных номеров
    phone_numbers = utils.search_phone_numbers(df)
    print("\nТранзакции с телефонными номерами:")
    print(phone_numbers)

    # Пример 5: Поиск переводов физическим лицам
    person_transfers = utils.search_person_transfers(df)
    print("\nПереводы физическим лицам:")
    print(person_transfers)
