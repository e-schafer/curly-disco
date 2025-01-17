import os
import time
from pprint import pp

from binance.spot import Spot

if __name__ == "__main__":
    api_key = os.environ["BINANCE_API_KEY"]
    api_secret = os.environ["BINANCE_API_SECRET"]

    spot = Spot(api_key, api_secret)

    # response = spot.new_order(symbol="USUALUSDT", side="BUY", type="LIMIT", quantity=20, price=0.48, timeInForce="GTC")
    response = spot.cancel_open_orders(symbol="USUALUSDT")
    pp(response)
