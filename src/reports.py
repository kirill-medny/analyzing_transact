import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Union

import pandas as pd
from pandas import DataFrame

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DEFAULT_REPORT_FILENAME = "report_{}.json"
REPORTS_DIRECTORY = "reports"

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


# Основная функция для "Отчеты"
def reports() -> None:
    """
    Главная функция для формирования отчетов для раздела "Отчеты".
    """
    # 1. Загрузка данных

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(project_root, "data", "operations.xlsx")
    df = pd.read_excel(data_path)

    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)
    df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)

    # 2. Пример использования
    report_date = "2021-11-15"  # Формат даты YYYY-MM-DD

    # Траты по категориям
    category = "Супермаркеты"
    spending_report = spending_by_category(df, category, report_date)
    print(f"Траты по категории '{category}':\n{spending_report}\n")

    # Траты по дням недели
    weekday_report = spending_by_weekday(df, report_date)
    print(f"Траты по дням недели:\n{weekday_report}\n")

    # Траты по выходным дням
    workday_report = spending_by_workday(df, report_date)
    print(f"Траты в рабочий/выходной день:\n{workday_report}\n")
