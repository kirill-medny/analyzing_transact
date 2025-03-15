import unittest
import pandas as pd
from datetime import datetime
from src import services
import json

class TestServices(unittest.TestCase):

    def setUp(self):
        # Sample DataFrame for testing
        data = {
            'Дата операции': [
                datetime(2023, 11, 10), datetime(2023, 11, 12), datetime(2023, 11, 15),
                datetime(2023, 10, 20), datetime(2023, 11, 5)
            ],
            'Сумма платежа': [
                -100.0, -250.0, -50.0,  # Expenses
                1000.0, 500.0  # Income
            ],
            'Сумма операции': [
                100.0, 250.0, 50.0,  # Expenses
                1000.0, 500.0  # Income
            ],
            'Категория': [
                'Food', 'Shopping', 'Food',
                'Salary', 'Bonus'
            ],
            'Описание': [
                'Grocery Store', 'Online Store', 'Cafe +7 921 111-22-33',
                'Monthly Salary', 'Bonus Валерий А.'
            ],
            'Номер карты': [1234, 5678, 1234, 4321, 8765]
        }
        self.df = pd.DataFrame(data)
        self.transactions = self.df.to_dict(orient="records")


    def test_analyze_cashback_categories(self):
        year = 2023
        month = 11
        cashback_analysis = services.analyze_cashback_categories(self.df, year, month)
        cashback_analysis_dict = json.loads(cashback_analysis)
        self.assertEqual(cashback_analysis_dict['Food'], 2)  # 100 + 50 = 150, 1% cashback is 1.5 round to 2
        self.assertEqual(cashback_analysis_dict['Shopping'], 3) # 250, 1% cashback is 2.5 round to 3


    def test_investment_bank(self):
        month = "2023-11"
        limit = 50
        investment_amount = services.investment_bank(month, self.transactions, limit)
        self.assertEqual(investment_amount, 30.0) # 100 -> 0, 250 -> 0, 50 -> 0, 500 -> 0 total is 0

        limit = 10
        investment_amount = services.investment_bank(month, self.transactions, limit)
        self.assertEqual(investment_amount, 6.0) # 100 -> 0, 250 -> 0, 50 -> 0, 500 -> 0 total is 0


    def test_simple_search(self):
        search_string = "Store"
        search_results = services.simple_search(search_string, self.df)
        search_results_list = json.loads(search_results)
        self.assertEqual(len(search_results_list), 2) # Grocery Store and Online Store


    def test_search_phone_numbers(self):
        phone_numbers = services.search_phone_numbers(self.df)
        phone_numbers_list = json.loads(phone_numbers)
        self.assertEqual(len(phone_numbers_list), 1) # One phone number in "Cafe" description


    def test_search_person_transfers(self):
        person_transfers = services.search_person_transfers(self.df)
        person_transfers_list = json.loads(person_transfers)
        self.assertEqual(len(person_transfers_list), 1) # One person transfer to "Валерий А."
