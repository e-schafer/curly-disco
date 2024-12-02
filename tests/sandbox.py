import os
from datetime import datetime
from pprint import pp

api_key = os.environ["API_KEY_WRITE"]
api_secret = os.environ["API_SECRET_WRITE"]


def test_api():
    from binance.spot import Spot

    _binance = Spot(api_key=api_key, api_secret=api_secret)
    # pp(list(filter(lambda x: x["status"] != "CANCELED", _binance.get_orders(symbol="ONGUSDT"))))
    # [print(y) for y in list(sorted(_binance.my_trades(symbol="ONGUSDT"), key=lambda x: x["time"]))]
    # pp(list(_binance.get_orders(symbol="ONGUSDT")))
    [
        print(y)
        for y in list(
            map(
                lambda x: {
                    "open_time": datetime.fromtimestamp(x[0] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                    "close_time": datetime.fromtimestamp(x[6] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                    "open": x[1],
                    "high": x[2],
                    "low": x[3],
                    "close": x[4],
                    "volume": x[5],
                    "quote_asset_volume": x[7],
                    "number_of_trades": x[8],
                },
                _binance.ui_klines(symbol="INJUSDT", interval="1d", limit=7),
            )
        )
    ]


if __name__ == "__main__":
    test_api()
