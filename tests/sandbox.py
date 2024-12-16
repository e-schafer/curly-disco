import os
from datetime import datetime
from pprint import pp

from binance.spot import Spot

api_key = os.environ["API_KEY_WRITE"]
api_secret = os.environ["API_SECRET_WRITE"]


if __name__ == "__main__":
    spot = Spot(api_key=api_key, api_secret=api_secret)
    # for order in spot.get_orders(symbol="DUSKUSDT"):
    #     order["time"] = datetime.fromtimestamp(order["time"] / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")
    #     if order["status"] == "FILLED":
    #         print(
    #             f" {order['symbol']}  {order['time']} {order['side']} {order['type']} {order['price']} {order['origQty']} {order['cummulativeQuoteQty']} {order['status']}"
    #         )
    # print("--------------------------------------------")
    # for trade in spot.my_trades(symbol="DUSKUSDT"):
    #     # print(trade)
    #     trade["time"] = datetime.fromtimestamp(trade["time"] / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")
    #     trade["side"] = "BUY" if trade["isBuyer"] else "SELL"
    #     print(
    #         f" {trade['symbol']}  {trade['time']} {trade['side']}  {trade['price']} {trade['qty']} {trade['quoteQty']} "
    #     )
    # print("--------------------------------------------")
    # for order in spot.get_orders(symbol="BLZUSDT"):
    #     order["time"] = datetime.fromtimestamp(order["time"] / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")
    #     if order["status"] == "CANCELED":
    #         print(order)
    # print("--------------------------------------------")
    # for info in spot.exchange_info(symbols=["WRXUSDT", "TROYUSDT"]).get("symbols"):
    #     info.pop("permissionSets")
    #     pp(info)
    x = (0.0000054154 // 0.0000001) * 0.0000001
    print(format(round(x, 8), "g"))
