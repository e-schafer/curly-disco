import os
import unittest
from pprint import pp

from bot import Bot
from tortoise import Tortoise

class TestBot(unittest.TestCase):
    def setUp(self):
        self.bot = Bot(
            api_key=os.environ["API_KEY_READONLY"],
            api_secret=os.environ["API_SECRET_READONLY"],
        )
        self.

    def test_get(self):
        response = self.bot.get_assets()
        pp(response)
        self.assertEqual(response, "Message sent: Hello")


if __name__ == "__main__":
    unittest.main()
