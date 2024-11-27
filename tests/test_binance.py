import os
from pprint import pp

from binance.spot import Spot

if __name__ == "__main__":
    client = Spot(
        api_key=os.getenv("API_KEY_READONLY"),
        api_secret=os.getenv("API_SECRET_READONLY"),
    )
    pp(client.exchange_info(symbol="DREPUSDT"))
