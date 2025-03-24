import logging
import os

import pandas as pd

from src import utils

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def reports() -> None:
    """
    Главная функция для формирования отчетов для раздела "Отчеты".
    """
    # 1. Загрузка данных
    # df = pd.read_excel("../data/operations.xlsx")

    file_path = os.path.join("..", "data", "operations.xlsx")
    df = pd.read_excel(file_path)

    # project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Поднимаемся на один уровень вверх от main.py
    # file_path = os.path.join(project_root, "operations.xlsx")
    # df = pd.read_excel(file_path)

    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)
    df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)

    # 2. Пример использования
    report_date = "2021-11-15"  # Формат даты YYYY-MM-DD

    # Траты по категориям
    category = "Супермаркеты"
    spending_report = utils.spending_by_category(df, category, report_date)
    print(f"Траты по категории '{category}':\n{spending_report}\n")

    # Траты по дням недели
    weekday_report = utils.spending_by_weekday(df, report_date)
    print(f"Траты по дням недели:\n{weekday_report}\n")

    # Траты по выходным дням
    workday_report = utils.spending_by_workday(df, report_date)
    print(f"Траты в рабочий/выходной день:\n{workday_report}\n")
