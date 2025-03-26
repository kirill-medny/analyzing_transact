import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd

from src.services import (analyze_cashback_categories, investment_bank,
                          search_person_transfers, search_phone_numbers,
                          simple_search)

# Тесты для analyze_cashback_categories


def test_analyze_cashback_categories_basic(sample_cashback_dataframe: pd.DataFrame) -> None:
    """
    Тест для базового случая с разными категориями и месяцем.
    """
    result = analyze_cashback_categories(sample_cashback_dataframe, year=2024, month=1)
    expected = {"A": 4, "B": 2}
    assert json.loads(result) == expected, "Неверный анализ кешбэка"


def test_analyze_cashback_categories_no_data(sample_cashback_dataframe: pd.DataFrame) -> None:
    """
    Тест, когда нет данных за указанный месяц.
    """
    result = analyze_cashback_categories(sample_cashback_dataframe, year=2023, month=1)
    expected: Dict[str, Any] = {}
    assert json.loads(result) == expected, "Должен возвращать пустой словарь, если нет данных"


def test_analyze_cashback_categories_only_positive_amounts(sample_cashback_dataframe: pd.DataFrame) -> None:
    """
    Тест, когда в DataFrame только положительные суммы (нет расходов).
    """
    positive_df = sample_cashback_dataframe.copy()
    positive_df["Сумма платежа"] = positive_df["Сумма платежа"].abs()
    result = analyze_cashback_categories(positive_df, year=2024, month=1)
    expected: Dict[str, Any] = {}  # Должен возвращать пустой словарь
    assert json.loads(result) == expected, "Должен возвращать пустой словарь, если нет расходов"


def test_analyze_cashback_categories_single_category(sample_cashback_dataframe: pd.DataFrame) -> None:
    """
    Тест, когда все расходы в одной категории.
    """
    single_category_df = sample_cashback_dataframe.copy()
    single_category_df["Категория"] = "Единственная категория"
    result = analyze_cashback_categories(single_category_df, year=2024, month=1)
    expected = {"Единственная категория": 6}  # Исправлено ожидаемое значение
    assert json.loads(result) == expected, "Неверный анализ кешбэка для одной категории"


def test_analyze_cashback_categories_multiple_months(sample_cashback_dataframe: pd.DataFrame) -> None:
    """
    Тест, когда данные за несколько месяцев, но анализируется только один.
    """
    result = analyze_cashback_categories(sample_cashback_dataframe, year=2024, month=2)
    expected = {"B": 4, "A": 5, "C": 6}  # Проверить расчет кешбека
    assert json.loads(result) == expected, "Неверный анализ кешбэка для одного месяца"


@patch("src.services.logging")  # Мокируем logging
def test_analyze_cashback_categories_exception_handling(
    mock_logging: MagicMock, sample_cashback_dataframe: pd.DataFrame
) -> None:
    """
    Тест для проверки обработки исключений.
    """
    # Создаем DataFrame с некорректным типом данных в столбце "Сумма платежа"
    bad_df = sample_cashback_dataframe.copy()
    bad_df["Сумма платежа"] = bad_df["Сумма платежа"].astype(str)  # Преобразуем в строку

    # Вызываем функцию analyze_cashback_categories с "плохим" DataFrame
    result = analyze_cashback_categories(bad_df, year=2024, month=1)

    # Проверяем, что возвращается JSON с информацией об ошибке
    result_dict = json.loads(result)
    assert "error" in result_dict, "Должно быть сообщение об ошибке"

    # Проверяем, что была запись в лог об исключении
    assert mock_logging.exception.called, "Должно быть записано в лог об исключении"


def test_analyze_cashback_categories_no_expenses(sample_cashback_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда все суммы доходов, а не расходов
    """
    income_only = sample_cashback_dataframe.copy()
    income_only["Сумма платежа"] = income_only["Сумма платежа"].abs()
    result = analyze_cashback_categories(income_only, year=2024, month=1)
    expected: Dict[str, Any] = {}
    assert json.loads(result) == expected, "Должен возвращать пустой словарь, если нет расходов"


def test_analyze_cashback_categories_rounding(sample_cashback_dataframe: pd.DataFrame) -> None:
    """
    Тест для проверки правильности округления значений кешбэка
    """

    # Создаем DataFrame с суммами, которые требуют округления
    data = {"Дата операции": [datetime(2024, 1, 5)], "Сумма платежа": [-50.50], "Категория": ["RoundingTest"]}
    rounding_df = pd.DataFrame(data)
    result = analyze_cashback_categories(rounding_df, year=2024, month=1)
    expected = {"RoundingTest": 1}
    assert json.loads(result) == expected, "Должен возвращать значения округленные до ближайшего целого"


# Тесты для investment_bank


def test_investment_bank_basic() -> None:
    """
    Тест для базового случая с несколькими транзакциями в одном месяце.
    """
    transactions = [
        {"Дата операции": datetime(2024, 1, 5), "Сумма операции": 123},
        {"Дата операции": datetime(2024, 1, 12), "Сумма операции": 250},
        {"Дата операции": datetime(2024, 1, 20), "Сумма операции": 75},
    ]
    limit = 100
    month = "2024-01"
    result = investment_bank(month, transactions, limit)
    assert result == 152.00, "Неверный расчет суммы для Инвесткопилки"  # 77 + 50 + 25


def test_investment_bank_no_transactions_for_month() -> None:
    """
    Тест, когда нет транзакций за указанный месяц.
    """
    transactions = [
        {"Дата операции": datetime(2023, 12, 5), "Сумма операции": 123},
        {"Дата операции": datetime(2023, 12, 12), "Сумма операции": 250},
    ]
    limit = 100
    month = "2024-01"
    result = investment_bank(month, transactions, limit)
    assert result == 0.0, "Должна быть возвращена сумма 0, если нет транзакций за указанный месяц"


def test_investment_bank_empty_transactions_list() -> None:
    """
    Тест для случая, когда список транзакций пустой.
    """
    transactions: List[Dict[str, Any]] = []
    limit = 100
    month = "2024-01"
    result = investment_bank(month, transactions, limit)
    assert result == 0.0, "Должна быть возвращена сумма 0, если список транзакций пустой"


def test_investment_bank_limit_is_one() -> None:
    """
    Тест, когда лимит равен 1.
    """
    transactions = [
        {"Дата операции": datetime(2024, 1, 5), "Сумма операции": 123},
        {"Дата операции": datetime(2024, 1, 12), "Сумма операции": 250},
    ]
    limit = 1
    month = "2024-01"
    result = investment_bank(month, transactions, limit)
    assert result == 0.0, "Должна быть возвращена сумма 0, если лимит равен 1"  # Улучшил этот тест


def test_investment_bank_transactions_with_same_date_different_amounts() -> None:
    """
    Тест, когда есть несколько транзакций с одной датой, но разными суммами.
    """
    transactions = [
        {"Дата операции": datetime(2024, 1, 5), "Сумма операции": 123},
        {"Дата операции": datetime(2024, 1, 5), "Сумма операции": 250},
    ]
    limit = 100
    month = "2024-01"
    result = investment_bank(month, transactions, limit)
    assert result == 127.00, "Неверный расчет суммы, когда есть несколько транзакций с одной датой"


def test_investment_bank_transactions_with_amounts_multiple_of_limit() -> None:
    """
    Тест, когда суммы операций кратны лимиту.
    """
    transactions = [
        {"Дата операции": datetime(2024, 1, 5), "Сумма операции": 100},
        {"Дата операции": datetime(2024, 1, 12), "Сумма операции": 200},
    ]
    limit = 100
    month = "2024-01"
    result = investment_bank(month, transactions, limit)
    assert result == 0.0, "Должна быть возвращена сумма 0, если суммы кратны лимиту"


@patch("src.services.logging")
def test_investment_bank_exception_handling(mock_logging: MagicMock) -> None:
    """
    Тест для проверки обработки исключений.
    """
    transactions = [
        {"Дата операции": "2024-01-05", "Сумма операции": 123},  # Некорректный формат даты
    ]
    limit = 100
    month = "2024-01"
    result = investment_bank(month, transactions, limit)
    assert result == 0.0, "Должна быть возвращена сумма 0 при ошибке"
    assert (
        mock_logging.exception.called
    ), "Должно быть записано в лог об исключении"  # Проверяем, что был вызов exception


# Тесты для simple_search


def test_simple_search_basic(sample_search_dataframe: pd.DataFrame) -> None:
    """
    Тест для базового поиска по строке.
    """
    search_string = "магазин"
    result = simple_search(search_string, sample_search_dataframe.copy())  # copy чтобы не менять фикстуру
    result_list = json.loads(result)
    assert len(result_list) == 2, "Должно быть найдено 2 транзакции"
    assert all(
        item["Описание"] in ["Покупка в магазине ABC", "Покупка в магазине DEF"] for item in result_list
    ), "Описание должно содержать 'магазин'"


def test_simple_search_case_insensitive(sample_search_dataframe: pd.DataFrame) -> None:
    """
    Тест для поиска без учета регистра.
    """
    search_string = "xYz"
    result = simple_search(search_string, sample_search_dataframe.copy())
    result_list = json.loads(result)
    assert len(result_list) == 1, "Должна быть найдена 1 транзакция"
    assert result_list[0]["Описание"] == "Оплата услуг XYZ", "Описание должно быть 'Оплата услуг XYZ'"


def test_simple_search_in_category(sample_search_dataframe: pd.DataFrame) -> None:
    """
    Тест для поиска по категории.
    """
    search_string = "Продукты"
    result = simple_search(search_string, sample_search_dataframe.copy())
    result_list = json.loads(result)
    assert len(result_list) == 2, "Должно быть найдено 2 транзакции"
    assert all(item["Категория"] == "Продукты" for item in result_list), "Категория должна быть 'Продукты'"


def test_simple_search_no_results(sample_search_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда нет результатов поиска.
    """
    search_string = "qwert"
    result = simple_search(search_string, sample_search_dataframe.copy())
    result_list = json.loads(result)
    assert len(result_list) == 0, "Должно быть найдено 0 транзакций"


def test_simple_search_empty_search_string(sample_search_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда поисковая строка пуста.  Должен вернуть все строки, так как все строки содержат ""
    """
    search_string = ""
    result = simple_search(search_string, sample_search_dataframe.copy())
    result_list = json.loads(result)
    assert len(result_list) == 4, "Должны быть найдены все транзакции"


@patch("src.services.logging")
def test_simple_search_exception_handling(mock_logging: MagicMock, sample_search_dataframe: pd.DataFrame) -> None:
    """
    Тест для проверки обработки исключений.
    """
    # Создаем DataFrame, где в столбце "Описание" будут числа,
    # что вызовет ошибку при применении str.contains
    bad_df = sample_search_dataframe.copy()
    bad_df["Описание"] = [1, 2, 3, 4]
    search_string = "магазин"  # Любая строка для поиска
    result = simple_search(search_string, bad_df)
    result_dict = json.loads(result)
    assert "error" in result_dict, "Должно быть сообщение об ошибке"
    assert mock_logging.exception.called, "Должно быть записано в лог об исключении"


# Тесты для search_phone_numbers


def test_search_phone_numbers_basic(sample_phone_dataframe: pd.DataFrame) -> None:
    """
    Тест для базового поиска телефонных номеров.
    """
    result = search_phone_numbers(sample_phone_dataframe.copy())
    result_list = json.loads(result)
    assert len(result_list) == 3, "Должно быть найдено 3 транзакции"
    assert all(
        item["Описание"]
        in [
            "Оплата по номеру +7 (912) 345-67-89",
            "Перевод другу 8 (903) 123 45 67",
            "Покупка в магазине, номер телефона +1234567890",
        ]
        for item in result_list
    ), "Описание должно содержать телефонный номер"


def test_search_phone_numbers_no_results(sample_phone_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда нет транзакций с телефонными номерами.
    """
    no_phone_df = sample_phone_dataframe.copy()
    no_phone_df["Описание"] = ["Обычная покупка"] * 4  # Меняем описания, чтобы не было номеров
    result = search_phone_numbers(no_phone_df)
    result_list = json.loads(result)
    assert len(result_list) == 0, "Должно быть найдено 0 транзакций"


def test_search_phone_numbers_different_formats(sample_phone_dataframe: pd.DataFrame) -> None:
    """
    Тест для поиска номеров в разных форматах (с пробелами, скобками и т.д.).
    """
    # Создаем DataFrame с разными форматами номеров
    data = {
        "Дата операции": [datetime(2024, 1, 5)],
        "Дата платежа": [datetime(2024, 1, 6)],
        "Описание": ["Номер: +1 (555)123-45-67, или 89001112233"],
        "Категория": ["Тест"],
        "Сумма платежа": [-10],
    }
    df = pd.DataFrame(data)
    result = search_phone_numbers(df.copy())
    result_list = json.loads(result)
    assert len(result_list) == 1, "Должна быть найдена 1 транзакция"
    assert result_list[0]["Описание"] == "Номер: +1 (555)123-45-67, или 89001112233", "Описание не соответствует"


def test_search_phone_numbers_empty_dataframe() -> None:
    """
    Тест для случая, когда DataFrame пустой.
    """
    empty_df = pd.DataFrame(
        {"Дата операции": [], "Дата платежа": [], "Описание": [], "Категория": [], "Сумма платежа": []}
    )
    result = search_phone_numbers(empty_df)
    result_list = json.loads(result)
    assert len(result_list) == 0, "Должно быть найдено 0 транзакций"


@patch("src.services.logging")
def test_search_phone_numbers_exception_handling(
    mock_logging: MagicMock, sample_phone_dataframe: pd.DataFrame
) -> None:
    """
    Тест для проверки обработки исключений.
    """
    # Создаем DataFrame, где столбец 'Описание' имеет некорректный тип
    bad_df = sample_phone_dataframe.copy()
    bad_df["Описание"] = [1, 2, 3, 4]
    result = search_phone_numbers(bad_df)
    result_dict = json.loads(result)
    assert "error" in result_dict, "Должно быть сообщение об ошибке"
    assert mock_logging.exception.called, "Должно быть записано в лог об исключении"


# Тесты для search_person_transfers


def test_search_person_transfers_basic(sample_person_transfers_dataframe: pd.DataFrame) -> None:
    """
    Тест для базового поиска переводов физлицам.
    """
    result = search_person_transfers(sample_person_transfers_dataframe.copy())
    result_list = json.loads(result)
    assert len(result_list) == 4, "Должно быть найдено 4 перевода физлицам"
    assert all(
        item["Описание"] in ["Перевод Иванову И.", "Перевод Петрову А.", "Перевод Сидорову Б.", "Перевод Орлову Г."]
        for item in result_list
    ), "Описание должно соответствовать переводу физлицу"


def test_search_person_transfers_no_results(sample_person_transfers_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда нет переводов физлицам.
    """
    no_person_transfers_df = sample_person_transfers_dataframe.copy()
    no_person_transfers_df["Описание"] = ["Оплата услуг"] * 5  # Меняем описания
    result = search_person_transfers(no_person_transfers_df)
    result_list = json.loads(result)
    assert len(result_list) == 0, "Должно быть найдено 0 переводов физлицам"


def test_search_person_transfers_wrong_category(sample_person_transfers_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда описание соответствует переводу, но категория не "Переводы".
    """
    wrong_category_df = sample_person_transfers_dataframe.copy()
    wrong_category_df["Категория"] = ["Покупки"] * 5  # Меняем категорию
    result = search_person_transfers(wrong_category_df)
    result_list = json.loads(result)
    assert len(result_list) == 0, "Должно быть найдено 0 переводов физлицам"


def test_search_person_transfers_empty_dataframe() -> None:
    """
    Тест для случая, когда DataFrame пустой.
    """
    empty_df = pd.DataFrame(
        {"Дата операции": [], "Дата платежа": [], "Описание": [], "Категория": [], "Сумма платежа": []}
    )
    result = search_person_transfers(empty_df)
    result_list = json.loads(result)
    assert len(result_list) == 0, "Должно быть найдено 0 переводов физлицам"


def test_search_person_transfers_invalid_name_format(sample_person_transfers_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда формат имени не соответствует (например, нет отчества).
    """
    invalid_name_df = sample_person_transfers_dataframe.copy()
    invalid_name_df["Описание"] = ["Перевод Иванов"] * 5  # Неправильный формат имени
    result = search_person_transfers(invalid_name_df)
    result_list = json.loads(result)
    assert len(result_list) == 0, "Должно быть найдено 0 переводов физлицам"


@patch("src.services.logging")
def test_search_person_transfers_exception_handling(
    mock_logging: MagicMock, sample_person_transfers_dataframe: pd.DataFrame
) -> None:
    """
    Тест для проверки обработки исключений.
    """
    # Создаем DataFrame, где столбец 'Описание' имеет некорректный тип
    bad_df = sample_person_transfers_dataframe.copy()
    bad_df["Описание"] = [1, 2, 3, 4, 5]
    result = search_person_transfers(bad_df)
    result_dict = json.loads(result)
    assert "error" in result_dict, "Должно быть сообщение об ошибке"
    assert mock_logging.exception.called, "Должно быть записано в лог об исключении"
