import os
from pprint import pp

api_key = os.environ["API_KEY_WRITE"]
api_secret = os.environ["API_SECRET_WRITE"]


def on_message(_, msg):
    print(_)
    print("------------")
    pp(msg)


def test_api():
    from binance.websocket.spot.websocket_api import SpotWebsocketAPIClient

    ws = SpotWebsocketAPIClient(
        api_key=api_key,
        api_secret=api_secret,
        on_message=on_message,
    )
    ws.ui_klines(symbol="BTCUSDT", interval="4h")


if __name__ == "__main__":
    test_api()
