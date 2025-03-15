import unittest
import pandas as pd
from datetime import datetime
from src import utils

class TestUtils(unittest.TestCase):

    def test_filter_transactions_by_month(self):
        data = {'Дата операции': [datetime(2023, 10, 1), datetime(2023, 10, 15), datetime(2023, 11, 1)],
                'Сумма платежа': [100, 200, 300]}
        df = pd.DataFrame(data)
        date = datetime(2023, 10, 20)
        filtered_df = utils.filter_transactions_by_month(df, date)
        self.assertEqual(len(filtered_df), 2) # Check that only October transactions are included
        self.assertEqual(filtered_df['Сумма платежа'].sum(), 300)

if __name__ == '__main__':
    unittest.main()

import unittest
import pandas as pd
from datetime import datetime, time
from src import views

class TestViews(unittest.TestCase):

    def setUp(self):
        # Sample DataFrame for testing
        data = {'Дата операции': [datetime(2023, 11, 10), datetime(2023, 11, 12), datetime(2023, 11, 15)],
                'Сумма платежа': [100.0, 250.0, 50.0],
                'Категория': ['Food', 'Shopping', 'Food'],
                'Описание': ['Grocery Store', 'Online Store', 'Cafe'],
                'Номер карты': [1234, 5678, 1234]}  # added 'Номер карты'
        self.df = pd.DataFrame(data)

    def test_get_greeting(self):
        self.assertEqual(views.get_greeting(time(8, 0)), "Доброе утро")
        self.assertEqual(views.get_greeting(time(14, 0)), "Добрый день")
        self.assertEqual(views.get_greeting(time(20, 0)), "Добрый вечер")
        self.assertEqual(views.get_greeting(time(2, 0)), "Доброй ночи")

    def test_get_card_data(self):
        card_data = views.get_card_data(self.df)
        self.assertEqual(len(card_data), 2)  # Two unique card numbers
        self.assertEqual(card_data[0]['last_digits'], '1234')
        self.assertEqual(card_data[0]['total_spent'], 150.0)
        self.assertEqual(card_data[0]['cashback'], 1.5)

    def test_get_top_transactions(self):
        top_transactions = views.get_top_transactions(self.df)
        self.assertEqual(len(top_transactions), 3)  # All 3 transactions are returned

        # Top transaction should be the one with the highest amount
        self.assertEqual(top_transactions[0]['amount'], 250.0)
        self.assertEqual(top_transactions[0]['category'], 'Shopping')
        self.assertEqual(top_transactions[0]['description'], 'Online Store')


if __name__ == '__main__':
    unittest.main()