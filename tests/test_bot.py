# genere un test pour la classe Bot avec pytest

import asyncio
import os

import pytest
from bot import Bot
from db import DB


@pytest.fixture
def autobot():
    return Bot(
        api_key=os.environ["API_KEY_WRITE"],
        api_secret=os.environ["API_SECRET_WRITE"],
    )


def test_first_run(autobot):
    asyncio.run(DB.init())
    asyncio.run(autobot.first_run())
    asyncio.run(DB.close())
    assert True
