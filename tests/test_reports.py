import unittest
import pandas as pd
from datetime import datetime
from src import reports
import os
import json

class TestReports(unittest.TestCase):

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
            'Категория': [
                'Food', 'Shopping', 'Food',
                'Salary', 'Bonus'
            ],
            'Описание': [
                'Grocery Store', 'Online Store', 'Cafe',
                'Monthly Salary', 'Performance Bonus'
            ],
            'Номер карты': [1234, 5678, 1234, 4321, 8765]
        }
        self.df = pd.DataFrame(data)
        self.report_date = "2023-11-15" # YYYY-MM-DD
        self.category = "Food"

    def test_spending_by_category(self):
        report = reports.spending_by_category(self.df, self.category, self.report_date)

        self.assertIsInstance(report, pd.DataFrame)
        self.assertFalse(report.empty)

        #  check that all categories are 'Food'
        self.assertTrue(all(self.df[self.df['Дата операции'] <= datetime.strptime(self.report_date, "%Y-%m-%d")]['Категория'] == self.category))


    def test_spending_by_weekday(self):
        report = reports.spending_by_weekday(self.df, self.report_date)
        self.assertIsInstance(report, pd.DataFrame)
        self.assertFalse(report.empty)

    def test_spending_by_workday(self):
        report = reports.spending_by_workday(self.df, self.report_date)
        self.assertIsInstance(report, pd.DataFrame)
        self.assertFalse(report.empty)

    def tearDown(self):
        # Clean up generated report files after tests (optional)
        for filename in os.listdir():
            if filename.startswith("report_") and filename.endswith(".json"):
                os.remove(filename)
        if os.path.exists("weekday_spending_report.json"):
            os.remove("weekday_spending_report.json")
