import json
from datetime import datetime, time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import requests
from pandas import DataFrame

from src.utils import (
    analyze_cashback_categories,
    filter_transactions_by_date_range,
    filter_transactions_by_month,
    get_card_data,
    get_currency_rates,
    get_date_range,
    get_expenses_data,
    get_greeting,
    get_income_data,
    get_top_transactions,
    investment_bank,
    search_person_transfers,
    search_phone_numbers,
    simple_search,
)

# Тесты для get_greeting


@pytest.mark.parametrize(
    "time_fixture, expected_greeting",
    [
        ("morning_time", "Доброе утро"),
        ("afternoon_time", "Добрый день"),
        ("evening_time", "Добрый вечер"),
        ("night_time", "Доброй ночи"),
    ],
)
def test_get_greeting_with_fixtures(time_fixture: str, expected_greeting: str, request: Any) -> None:
    """
    Тест функции get_greeting с использованием фикстур для времени.
    """
    current_time = request.getfixturevalue(time_fixture)  # Получаем значение фикстуры
    greeting = get_greeting(current_time)
    assert (
        greeting == expected_greeting
    ), f"Для времени {current_time} ожидалось приветствие '{expected_greeting}', но было получено '{greeting}'"


@pytest.mark.parametrize(
    "hour, expected_greeting",
    [
        (6, "Доброе утро"),
        (11, "Доброе утро"),
        (12, "Добрый день"),
        (17, "Добрый день"),
        (18, "Добрый вечер"),
        (22, "Добрый вечер"),
        (23, "Доброй ночи"),
        (5, "Доброй ночи"),
        (0, "Доброй ночи"),
    ],
)
def test_get_greeting_with_hours(hour: int, expected_greeting: str) -> None:
    """
    Тест функции get_greeting с параметризацией по часу.
    """
    current_time = time(hour=hour, minute=0, second=0)
    greeting = get_greeting(current_time)
    assert (
        greeting == expected_greeting
    ), f"Для часа {hour} ожидалось приветствие '{expected_greeting}', но было получено '{greeting}'"


@patch("src.utils.time")  # Замените src.utils на фактический путь к модулю
def test_get_greeting_mock_time(mock_time: MagicMock) -> None:
    """
    Тест функции get_greeting с использованием Mock для времени.
    """
    mock_time.return_value.hour = 10  # Устанавливаем час для мокированного времени
    greeting = get_greeting(mock_time.return_value)
    assert greeting == "Доброе утро"


# Тесты для get_card_data


def test_get_card_data_empty_dataframe() -> None:
    """
    Тест для случая, когда DataFrame пустой.
    """
    empty_df = pd.DataFrame({"Номер карты": [], "Сумма платежа": []})
    result = get_card_data(empty_df)
    assert result == [], "Для пустого DataFrame должен возвращаться пустой список"


def test_get_card_data_single_card(sample_dataframe: DataFrame) -> None:
    """
    Тест для случая, когда DataFrame содержит данные только по одной карте.
    """
    single_card_df = sample_dataframe[sample_dataframe["Номер карты"] == "*1234"]
    result = get_card_data(single_card_df)
    assert len(result) == 1, "Должна быть информация только по одной карте"
    assert result[0]["last_digits"] == "*1234", "Неверный номер карты"
    assert result[0]["total_spent"] == -125.0, "Неверная общая сумма расходов"
    assert result[0]["cashback"] == -1.25, "Неверный кешбэк"


def test_get_card_data_multiple_cards(sample_dataframe: DataFrame) -> None:
    """
    Тест для случая, когда DataFrame содержит данные по нескольким картам.
    """
    result = get_card_data(sample_dataframe)
    assert len(result) == 3, "Должна быть информация по трем картам"
    card_numbers = [card["last_digits"] for card in result]
    assert "*1234" in card_numbers, "Номер карты *1234 отсутствует"
    assert "*5678" in card_numbers, "Номер карты *5678 отсутствует"
    assert "*9012" in card_numbers, "Номер карты *9012 отсутствует"

    # Проверка сумм для карты *1234
    card_1234_data = next(card for card in result if card["last_digits"] == "*1234")
    assert card_1234_data["total_spent"] == -125.0, "Неверная общая сумма расходов для карты *1234"
    assert card_1234_data["cashback"] == -1.25, "Неверный кешбэк для карты *1234"


@pytest.mark.parametrize(
    "card_number, expected_total_spent, expected_cashback",
    [
        ("*1234", -125.0, -1.25),
        ("*5678", -60.0, -0.6),
        ("*9012", -75.0, -0.75),
    ],
)
def test_get_card_data_parameterized(
    sample_dataframe: DataFrame,
    card_number: str,
    expected_total_spent: float,
    expected_cashback: float,
) -> None:
    """
    Параметризованный тест для проверки данных по каждой карте.
    """
    result = get_card_data(sample_dataframe)
    card_data = next((card for card in result if card["last_digits"] == card_number), None)
    assert card_data is not None, f"Данные для карты {card_number} не найдены"
    assert card_data["total_spent"] == expected_total_spent, f"Неверная общая сумма расходов для карты {card_number}"
    assert card_data["cashback"] == expected_cashback, f"Неверный кешбэк для карты {card_number}"


@patch("pandas.core.series.Series.unique")
def test_get_card_data_mock_unique(mock_unique: MagicMock, sample_dataframe: DataFrame) -> None:
    """
    Тест с использованием Mock для метода unique.
    """
    # Мокируем возвращаемое значение метода unique для столбца 'Номер карты'
    mock_unique.return_value = ["*1234"]

    # Запускаем тестируемую функцию
    result = get_card_data(sample_dataframe)

    # Проверяем, что метод unique был вызван
    mock_unique.assert_called_once()  # или assert mock_unique.call_count == 1

    # Проверяем результат работы функции
    assert len(result) == 1, "Должна быть информация только по одной карте"
    assert result[0]["last_digits"] == "*1234", "Неверный номер карты"


# Тесты для get_top_transactions


def test_get_top_transactions_empty_dataframe() -> None:
    """
    Тест для случая, когда DataFrame пустой.
    """
    empty_df = pd.DataFrame({"Дата операции": [], "Сумма платежа": [], "Категория": [], "Описание": []})
    result = get_top_transactions(empty_df)
    assert result == [], "Для пустого DataFrame должен возвращаться пустой список"


def test_get_top_transactions_less_than_5_transactions(sample_dataframe_top_transactions: pd.DataFrame) -> None:
    """
    Тест, когда в DataFrame меньше 5 транзакций.
    """
    df = sample_dataframe_top_transactions.sort_values(by="Сумма платежа", ascending=True).head(
        3
    )  # Сначала сортируем, потом берем 3 строки
    result = get_top_transactions(df)
    assert len(result) == 3, "Должно быть возвращено 3 транзакции"
    assert result[0]["amount"] == -800.00, "Неверная сортировка (первая транзакция)"
    assert result[1]["amount"] == -564.00, "Неверная сортировка (вторая транзакция)"
    assert result[2]["amount"] == -160.89, "Неверная сортировка (третья транзакция)"


def test_get_top_transactions_exactly_5_transactions(sample_dataframe_top_transactions: pd.DataFrame) -> None:
    """
    Тест, когда в DataFrame ровно 5 транзакций.
    """
    df = sample_dataframe_top_transactions.sort_values(by="Сумма платежа", ascending=True).head(5)
    result = get_top_transactions(df)
    assert len(result) == 5, "Должно быть возвращено 5 транзакций"
    assert result[0]["amount"] == -800.00, "Неверная сортировка (первая транзакция)"
    assert result[1]["amount"] == -564.00, "Неверная сортировка (вторая транзакция)"
    assert result[2]["amount"] == -160.89, "Неверная сортировка (третья транзакция)"
    assert result[3]["amount"] == -118.12, "Неверная сортировка (четвертая транзакция)"
    assert result[4]["amount"] == -78.05, "Неверная сортировка (пятая транзакция)"


def test_get_top_transactions_more_than_5_transactions(sample_dataframe_top_transactions: pd.DataFrame) -> None:
    """
    Тест, когда в DataFrame больше 5 транзакций.
    """
    df = sample_dataframe_top_transactions.sort_values(by="Сумма платежа", ascending=True)
    result = get_top_transactions(df)
    assert len(result) == 5, "Должно быть возвращено 5 транзакций"
    assert result[0]["amount"] == -800.00, "Неверная сортировка (первая транзакция)"
    assert result[1]["amount"] == -564.00, "Неверная сортировка (вторая транзакция)"
    assert result[2]["amount"] == -160.89, "Неверная сортировка (третья транзакция)"
    assert result[3]["amount"] == -118.12, "Неверная сортировка (четвертая транзакция)"
    assert result[4]["amount"] == -78.05, "Неверная сортировка (пятая транзакция)"


def test_get_top_transactions_date_format(sample_dataframe_top_transactions: pd.DataFrame) -> None:
    """
    Тест, что дата отформатирована правильно.
    """
    result = get_top_transactions(sample_dataframe_top_transactions)
    for transaction in result:
        assert isinstance(transaction["date"], str), "Дата должна быть строкой"
        assert len(transaction["date"]) == 10, "Длина строки даты должна быть 10 символов"
        assert transaction["date"][2] == ".", "Разделитель в дате должен быть точкой"
        assert transaction["date"][5] == ".", "Разделитель в дате должен быть точкой"


# Тесты для get_currency_rates


def test_get_currency_rates_success(currencies: List[str], mock_response: MagicMock) -> None:
    """
    Тест для успешного получения курсов валют.
    """
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        result = get_currency_rates(currencies)
        assert "USD" in result, "USD должен быть в результатах"
        assert "EUR" in result, "EUR должен быть в результатах"
        assert "GBP" in result, "GBP должен быть в результатах"
        assert "RUB" not in result, "RUB не должен быть в результатах"
        assert result["USD"] == 75.0, "Неверный курс USD"
        assert result["EUR"] == 85.0, "Неверный курс EUR"
        assert result["GBP"] == 100.0, "Неверный курс GBP"


def test_get_currency_rates_api_error(currencies: List[str]) -> None:
    """
    Тест для случая, когда API возвращает ошибку.
    """
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        result = get_currency_rates(currencies)
        assert "USD" in result, "USD должен быть в результатах"
        assert "EUR" in result, "EUR должен быть в результатах"
        assert "GBP" in result, "GBP должен быть в результатах"
        assert result["USD"] is None, "Курс USD должен быть None при ошибке API"
        assert result["EUR"] is None, "Курс EUR должен быть None при ошибке API"
        assert result["GBP"] is None, "Курс GBP должен быть None при ошибке API"


def test_get_currency_rates_rub_excluded(currencies: List[str]) -> None:
    """
    Тест, что RUB исключается из запросов к API.
    """
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {}  # Пустой ответ, чтобы тест был минимальным
        result = get_currency_rates(currencies)

        # Проверка количества вызовов
        assert mock_get.call_count == 3, "Должно быть 3 запроса (USD, EUR, GBP)"

        # Проверка URL (чтобы RUB не было в запросах)
        for call in mock_get.call_args_list:
            url = call[0][0]  # Получаем URL из аргументов вызова
            assert "RUB" not in url, f"Запрос к API содержит RUB: {url}"

        # Проверка возвращаемого значения (добавлено)
        assert isinstance(result, dict), "Должен возвращаться словарь"
        assert len(result) == 3, "Должно быть 3 элемента в словаре (USD, EUR, GBP)"
        assert all(key in result for key in ["USD", "EUR", "GBP"]), "Словарь должен содержать ключи USD, EUR, GBP"
        assert all(value is None for value in result.values()), "Значения должны быть None (т.к. ответ пустой)"


@pytest.mark.parametrize(
    "currency, expected_value",
    [
        ("USD", 75.0),
        ("EUR", 85.0),
        ("GBP", 100.0),
    ],
)
def test_get_currency_rates_parameterized(
    currencies: List[str], mock_response: Dict[str, Any], currency: str, expected_value: float
) -> None:
    """
    Параметризованный тест для проверки курса каждой валюты.
    """
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        result = get_currency_rates(currencies)
        assert result[currency] == expected_value, f"Неверный курс для {currency}"


# Тесты для get_stock_data


# Тесты для filter_transactions_by_month


def test_filter_transactions_by_month_empty_dataframe() -> None:
    """
    Тест для случая, когда DataFrame пустой.
    """
    empty_df = pd.DataFrame({"Дата операции": [], "Сумма платежа": [], "Категория": []})
    date = datetime(2024, 1, 15)
    result = filter_transactions_by_month(empty_df, date)
    assert result.empty, "Для пустого DataFrame должен возвращаться пустой DataFrame"


def test_filter_transactions_by_month_single_month(sample_dataframe_by_month: pd.DataFrame) -> None:
    """
    Тест для фильтрации транзакций в пределах одного месяца.
    """
    date = datetime(2024, 1, 15)
    result = filter_transactions_by_month(sample_dataframe_by_month, date)
    assert len(result) == 2, "Должно быть возвращено 2 транзакции"
    assert (result["Дата операции"] <= date).all(), "Все даты должны быть до указанной даты"
    assert (result["Дата операции"] >= datetime(2024, 1, 1)).all(), "Все даты должны быть в январе"


def test_filter_transactions_by_month_same_date_as_transaction(sample_dataframe_by_month: pd.DataFrame) -> None:
    """
    Тест, когда указанная дата совпадает с датой одной из транзакций.
    """
    date = datetime(2024, 1, 20)
    result = filter_transactions_by_month(sample_dataframe_by_month, date)
    assert len(result) == 3, "Должно быть возвращено 3 транзакции"
    assert date in result["Дата операции"].tolist(), "Должна быть транзакция за 20 января"


def test_filter_transactions_by_month_date_at_start_of_month(sample_dataframe_by_month: pd.DataFrame) -> None:
    """
    Тест, когда указана дата в начале месяца.
    """
    date = datetime(2024, 1, 1)
    result = filter_transactions_by_month(sample_dataframe_by_month, date)
    assert len(result) == 0, "Должно быть возвращено 0 транзакций, так как ни одна дата меньше 1 января"


def test_filter_transactions_by_month_date_at_end_of_month(sample_dataframe_by_month: pd.DataFrame) -> None:
    """
    Тест, когда указана дата в конце месяца.
    """
    date = datetime(2024, 1, 31)  # Предполагаем, что в sample_dataframe нет данных за январь
    result = filter_transactions_by_month(sample_dataframe_by_month, date)
    assert len(result) == 3, "Должно быть возвращено 3 транзакции (январь)"
    assert (result["Дата операции"] <= date).all(), "Все даты должны быть до указанной даты"
    assert (result["Дата операции"] >= datetime(2024, 1, 1)).any(), "Должна быть хотя бы одна дата в январе"


# Тесты для get_date_range


def test_get_date_range_week() -> None:
    """
    Тест для диапазона дат "неделя".
    """
    date = datetime(2024, 2, 20)  # Вторник
    start_date, end_date = get_date_range(date, data_range="W")
    assert start_date == datetime(2024, 2, 19), "Начало недели должно быть 19 февраля"
    assert end_date == datetime(2024, 2, 25), "Конец недели должен быть 25 февраля"


def test_get_date_range_month() -> None:
    """
    Тест для диапазона дат "месяц".
    """
    date = datetime(2024, 2, 20)
    start_date, end_date = get_date_range(date, data_range="M")
    assert start_date == datetime(2024, 2, 1), "Начало месяца должно быть 1 февраля"
    assert end_date == datetime(2024, 2, 20), "Конец месяца должен быть 20 февраля"


def test_get_date_range_year() -> None:
    """
    Тест для диапазона дат "год".
    """
    date = datetime(2024, 2, 20)
    start_date, end_date = get_date_range(date, data_range="Y")
    assert start_date == datetime(2024, 1, 1), "Начало года должно быть 1 января"
    assert end_date == datetime(2024, 2, 20), "Конец года должен быть 20 февраля"


def test_get_date_range_all() -> None:
    """
    Тест для диапазона дат "все данные".
    """
    date = datetime(2024, 2, 20)
    start_date, end_date = get_date_range(date, data_range="ALL")
    assert start_date == datetime.min, "Начало периода должно быть min datetime"
    assert end_date == datetime(2024, 2, 20), "Конец периода должен быть 20 февраля"


def test_get_date_range_default() -> None:
    """
    Тест для диапазона дат по умолчанию ("месяц").
    """
    date = datetime(2024, 2, 20)
    start_date, end_date = get_date_range(date)
    assert start_date == datetime(2024, 2, 1), "Начало месяца должно быть 1 февраля"
    assert end_date == datetime(2024, 2, 20), "Конец месяца должен быть 20 февраля"


def test_get_date_range_invalid_range() -> None:
    """
    Тест для неверного диапазона дат.
    """
    date = datetime(2024, 2, 20)
    with pytest.raises(ValueError, match="Неверный диапазон данных. Допустимые значения: W, M, Y, ALL"):
        get_date_range(date, data_range="INVALID")


def test_get_date_range_week_start_of_week() -> None:
    """
    Тест для диапазона дат "неделя", когда дата приходится на начало недели.
    """
    date = datetime(2024, 2, 19)  # Понедельник
    start_date, end_date = get_date_range(date, data_range="W")
    assert start_date == datetime(2024, 2, 19), "Начало недели должно быть 19 февраля"
    assert end_date == datetime(2024, 2, 25), "Конец недели должен быть 25 февраля"


def test_get_date_range_week_end_of_week() -> None:
    """
    Тест для диапазона дат "неделя", когда дата приходится на конец недели.
    """
    date = datetime(2024, 2, 25)  # Воскресенье
    start_date, end_date = get_date_range(date, data_range="W")
    assert start_date == datetime(2024, 2, 19), "Начало недели должно быть 19 февраля"
    assert end_date == datetime(2024, 2, 25), "Конец недели должен быть 25 февраля"


# Тесты для filter_transactions_by_date_range


def test_filter_transactions_by_date_range_empty_dataframe() -> None:
    """
    Тест для случая, когда DataFrame пустой.
    """
    empty_df = pd.DataFrame({"Дата операции": [], "Сумма платежа": [], "Категория": []})
    start_date = datetime(2024, 1, 10)
    end_date = datetime(2024, 1, 20)
    result = filter_transactions_by_date_range(empty_df, start_date, end_date)
    assert result.empty, "Для пустого DataFrame должен возвращаться пустой DataFrame"


def test_filter_transactions_by_date_range_within_range(sample_dataframe_by_month: pd.DataFrame) -> None:
    """
    Тест для фильтрации по датам, находящимся внутри диапазона.
    """
    start_date = datetime(2024, 1, 10)
    end_date = datetime(2024, 1, 20)
    result = filter_transactions_by_date_range(sample_dataframe_by_month, start_date, end_date)
    assert len(result) == 2, "Должно быть возвращено 2 транзакции"
    assert (result["Дата операции"] >= start_date).all(), "Все даты должны быть больше или равны start_date"
    assert (result["Дата операции"] <= end_date).all(), "Все даты должны быть меньше или равны end_date"


def test_filter_transactions_by_date_range_end_date_at_end(sample_dataframe_by_month: pd.DataFrame) -> None:
    """
    Тест, когда end_date совпадает с датой транзакции.
    """
    start_date = datetime(2024, 1, 12)
    end_date = datetime(2024, 1, 20)
    result = filter_transactions_by_date_range(sample_dataframe_by_month, start_date, end_date)
    assert len(result) == 2, "Должно быть возвращено 2 транзакции"
    assert (result["Дата операции"] >= start_date).all(), "Все даты должны быть больше или равны start_date"
    assert (result["Дата операции"] <= end_date).all(), "Все даты должны быть меньше или равны end_date"
    end_date_np = np.datetime64(end_date)  # Преобразуем datetime в datetime64
    assert end_date_np in result["Дата операции"].values, "Должна быть транзакция за 20 января"


def test_filter_transactions_by_date_range_range_covers_multiple_months(
    sample_dataframe_by_month: pd.DataFrame,
) -> None:
    """
    Тест, когда диапазон дат охватывает несколько месяцев.
    """
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 2, 28)
    result = filter_transactions_by_date_range(sample_dataframe_by_month, start_date, end_date)
    assert len(result) == 5, "Должно быть возвращено 5 транзакций"
    assert (result["Дата операции"] >= start_date).all(), "Все даты должны быть больше или равны start_date"
    assert (result["Дата операции"] <= end_date).all(), "Все даты должны быть меньше или равны end_date"
    assert (
        result["Дата операции"].dt.month <= 2
    ).all(), "Все месяцы должны быть январь или февраль"  # Дополнительная проверка


def test_filter_transactions_by_date_range_no_matches(sample_dataframe_by_month: pd.DataFrame) -> None:
    """
    Тест, когда нет транзакций в указанном диапазоне.
    """
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 31)
    result = filter_transactions_by_date_range(sample_dataframe_by_month, start_date, end_date)
    assert result.empty, "Должен вернуться пустой DataFrame, так как нет совпадений"


def test_filter_transactions_by_date_range_start_date_greater_than_end_date(
    sample_dataframe_by_month: pd.DataFrame,
) -> None:
    """
    Тест для случая, когда start_date больше end_date (должен вернуть пустой DataFrame).
    """
    start_date = datetime(2024, 1, 20)
    end_date = datetime(2024, 1, 10)
    result = filter_transactions_by_date_range(sample_dataframe_by_month, start_date, end_date)
    assert result.empty, "Должен вернуться пустой DataFrame"


# Тесты для get_expenses_data


def test_get_expenses_data_empty_dataframe() -> None:
    """
    Тест для случая, когда DataFrame пустой.
    """
    empty_df = pd.DataFrame({"Дата операции": [], "Сумма платежа": [], "Категория": []})
    result = get_expenses_data(empty_df)
    assert result["total_amount"] == 0, "Общая сумма должна быть 0 для пустого DataFrame"
    assert len(result["main"]) == 1, "Должен быть только элемент 'Остальное' в main"
    assert result["main"][0]["category"] == "Остальное", "Категория должна быть 'Остальное'"
    assert result["main"][0]["amount"] == 0, "Сумма в 'Остальное' должна быть 0"
    assert len(result["transfers_and_cash"]) == 2, "Должно быть два элемента в transfers_and_cash"
    assert result["transfers_and_cash"][0]["category"] == "Наличные"
    assert result["transfers_and_cash"][0]["amount"] == 0
    assert result["transfers_and_cash"][1]["category"] == "Переводы"
    assert result["transfers_and_cash"][1]["amount"] == 0


def test_get_expenses_data_basic(sample_expenses_dataframe: pd.DataFrame) -> None:
    """
    Тест для базового случая с расходами по разным категориям.
    """
    result = get_expenses_data(sample_expenses_dataframe)
    assert result["total_amount"] == -210, "Общая сумма расходов должна быть -210"

    # Проверяем main
    assert len(result["main"]) == 3, "Должно быть 2 категории + 'Остальное'"
    assert result["main"][0]["category"] == "A", "Первая категория должна быть A"
    assert result["main"][0]["amount"] == 90, "Сумма для A должна быть 90"
    assert result["main"][1]["category"] == "B", "Вторая категория должна быть B"
    assert result["main"][1]["amount"] == 60, "Сумма для B должна быть 60"
    assert result["main"][2]["category"] == "Остальное", "Последняя категория должна быть 'Остальное'"
    assert result["main"][2]["amount"] == 0, "Сумма для 'Остальное' должна быть 0"

    # Проверяем transfers_and_cash
    assert len(result["transfers_and_cash"]) == 2, "Должно быть два элемента в transfers_and_cash"
    assert result["transfers_and_cash"][0]["category"] == "Наличные", "Первая категория должна быть 'Наличные'"
    assert result["transfers_and_cash"][0]["amount"] == 60, "Сумма для 'Наличные' должна быть 60"
    assert result["transfers_and_cash"][1]["category"] == "Переводы", "Вторая категория должна быть 'Переводы'"
    assert result["transfers_and_cash"][1]["amount"] == 0, "Сумма для 'Переводы' должна быть 0"


def test_get_expenses_data_only_positive_amounts(sample_expenses_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда в DataFrame только положительные суммы (доходы).
    """
    positive_df = sample_expenses_dataframe.copy()
    positive_df["Сумма платежа"] = positive_df["Сумма платежа"].abs()  # делаем все суммы положительными
    result = get_expenses_data(positive_df)
    assert result["total_amount"] == 0, "Общая сумма должна быть 0, если нет расходов"
    assert len(result["main"]) == 1, "Должен быть только 'Остальное', если нет расходов"
    assert result["transfers_and_cash"][0]["amount"] == 0, "Суммы должны быть нулевыми"
    assert result["transfers_and_cash"][1]["amount"] == 0, "Суммы должны быть нулевыми"


def test_get_expenses_data_transfers_and_cash_categories(sample_expenses_dataframe: pd.DataFrame) -> None:
    """
    Тест для проверки правильности расчета сумм для категорий "Наличные" и "Переводы".
    """
    # Добавляем переводы
    transfers_data = {"Дата операции": [datetime(2024, 1, 2)], "Сумма платежа": [-25], "Категория": ["Переводы"]}
    transfers_df = pd.DataFrame(transfers_data)
    df = pd.concat([sample_expenses_dataframe, transfers_df], ignore_index=True)

    result = get_expenses_data(df)

    assert result["transfers_and_cash"][0]["category"] == "Наличные", "Первая категория должна быть 'Наличные'"
    assert result["transfers_and_cash"][0]["amount"] == 60, "Сумма для 'Наличные' должна быть 60"
    assert result["transfers_and_cash"][1]["category"] == "Переводы", "Вторая категория должна быть 'Переводы'"
    assert result["transfers_and_cash"][1]["amount"] == 25, "Сумма для 'Переводы' должна быть 25"


def test_get_expenses_data_top_categories_limit(sample_expenses_dataframe: pd.DataFrame) -> None:
    """
    Тест для проверки, что возвращаются только топ-7 категорий + "Остальное".
    """
    # Создаем DataFrame с более чем 7 категориями (чтобы проверить лимит)
    data: Dict[str, List[Any]] = {"Дата операции": [], "Сумма платежа": [], "Категория": []}
    for i in range(10):
        data["Дата операции"].append(datetime(2024, 1, i + 1))
        data["Сумма платежа"].append(-i * 10)
        data["Категория"].append(f"Категория {i}")

    many_categories_df = pd.DataFrame(data)
    result = get_expenses_data(many_categories_df)
    assert len(result["main"]) == 8, "Должно быть 7 топ-категорий + 'Остальное'"
    assert result["main"][-1]["category"] == "Остальное", "'Остальное' должно быть последней категорией"


def test_get_expenses_data_no_transfers_or_cash(sample_expenses_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда в DataFrame нет категорий "Наличные" и "Переводы".
    """
    no_transfers_df = sample_expenses_dataframe[sample_expenses_dataframe["Категория"] != "Наличные"].copy()
    result = get_expenses_data(no_transfers_df)
    assert result["transfers_and_cash"][0]["amount"] == 0, "Сумма для 'Наличные' должна быть 0"
    assert result["transfers_and_cash"][1]["amount"] == 0, "Сумма для 'Переводы' должна быть 0"


def test_get_expenses_data_same_category_name(sample_expenses_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда категория "Остальное" уже есть в данных
    """
    new_data = {"Дата операции": [datetime(2024, 1, 1)], "Сумма платежа": [-50], "Категория": ["Остальное"]}
    new_df = pd.DataFrame(new_data)
    combined_df = pd.concat([sample_expenses_dataframe, new_df], ignore_index=True)

    result = get_expenses_data(combined_df)
    assert "Остальное" in [cat["category"] for cat in result["main"]], "Должна быть категория 'Остальное'"


# Тесты для get_income_data


def test_get_income_data_empty_dataframe() -> None:
    """
    Тест для случая, когда DataFrame пустой.
    """
    empty_df = pd.DataFrame({"Дата операции": [], "Сумма платежа": [], "Категория": []})
    result = get_income_data(empty_df)
    assert result["total_amount"] == 0, "Общая сумма должна быть 0 для пустого DataFrame"
    assert len(result["main"]) == 0, "Список категорий должен быть пустым для пустого DataFrame"


def test_get_income_data_basic(sample_income_dataframe: pd.DataFrame) -> None:
    """
    Тест для базового случая с доходами по разным категориям.
    """
    result = get_income_data(sample_income_dataframe)
    assert result["total_amount"] == 2100, "Общая сумма доходов должна быть 2100"
    assert len(result["main"]) == 3, "Должно быть 3 категории доходов"

    # Проверяем порядок и суммы категорий (учитываем сортировку)
    assert result["main"][0]["category"] == "Зарплата", "Первая категория должна быть Зарплата"
    assert result["main"][0]["amount"] == 900, "Сумма для Зарплаты должна быть 900"
    assert result["main"][1]["category"] == "Инвестиции", "Вторая категория должна быть Инвестиции"
    assert result["main"][1]["amount"] == 600, "Сумма для Инвестиций должна быть 600"
    assert result["main"][2]["category"] == "Подработка", "Третья категория должна быть Подработка"
    assert result["main"][2]["amount"] == 600, "Сумма для Подработки должна быть 600"  # Раньше была ошибка


def test_get_income_data_only_negative_amounts(sample_income_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда в DataFrame только отрицательные суммы (расходы).
    """
    negative_df = sample_income_dataframe.copy()
    negative_df["Сумма платежа"] = -negative_df["Сумма платежа"]  # делаем все суммы отрицательными
    result = get_income_data(negative_df)
    assert result["total_amount"] == 0, "Общая сумма должна быть 0, если нет доходов"
    assert len(result["main"]) == 0, "Список категорий должен быть пустым, если нет доходов"


def test_get_income_data_single_category(sample_income_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда все доходы относятся к одной категории.
    """
    single_category_df = sample_income_dataframe.copy()
    single_category_df["Категория"] = "Единственный доход"
    result = get_income_data(single_category_df)
    assert result["total_amount"] == 2100, "Общая сумма должна быть 2100"
    assert len(result["main"]) == 1, "Должна быть только одна категория"
    assert result["main"][0]["category"] == "Единственный доход", "Категория должна быть 'Единственный доход'"
    assert result["main"][0]["amount"] == 2100, "Сумма для 'Единственный доход' должна быть 2100"


def test_get_income_data_zero_amounts(sample_income_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда в DataFrame есть нулевые суммы (они должны игнорироваться).
    """
    zero_amounts_data = {"Дата операции": [datetime(2024, 1, 1)], "Сумма платежа": [0], "Категория": ["Не учитывать"]}
    zero_amounts_df = pd.DataFrame(zero_amounts_data)
    df = pd.concat([sample_income_dataframe, zero_amounts_df], ignore_index=True)  # добавляем нулевые суммы
    result = get_income_data(df)
    assert result["total_amount"] == 2100, "Общая сумма должна быть 2100 (нули игнорируются)"
    # Проверяем, что категория "Не учитывать" отсутствует:
    category_names = [item["category"] for item in result["main"]]
    assert "Не учитывать" not in category_names


def test_get_income_data_empty_categories(sample_income_dataframe: pd.DataFrame) -> None:
    """
    Тест для случая, когда в DataFrame есть пустые категории
    """
    empty_category_data = {"Дата операции": [datetime(2024, 1, 1)], "Сумма платежа": [100], "Категория": [""]}
    empty_category_df = pd.DataFrame(empty_category_data)
    df = pd.concat([sample_income_dataframe, empty_category_df], ignore_index=True)
    result = get_income_data(df)
    assert "" in [item["category"] for item in result["main"]], "Пустая категория должна присутствовать"


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


@patch("src.utils.logging")  # Мокируем logging
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


@patch("src.utils.logging")
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


@patch("src.utils.logging")
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


@patch("src.utils.logging")
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


@patch("src.utils.logging")
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


# Тесты для report_decorator


# Тесты для report_decorator
