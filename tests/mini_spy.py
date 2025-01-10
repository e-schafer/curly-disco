import time

from binance.spot import Spot
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient


class MiniSpy:
    def __init__(self, api_key, api_secret):
        self.client: Spot = Spot(api_key, api_secret)

        self.ws_client = SpotWebsocketStreamClient(on_message=self.on_message)
        self.listen_key = self.client.new_listen_key()["listenKey"]
        self.ws_client.user_data(listen_key=self.listen_key)
        print("started")

    def on_message(self, _, msg):
        print(f"on_message: {msg}")
        with open("mini_spy.log", "a") as f:
            f.write(f"{msg}\n")


if __name__ == "__main__":
    import os

    api_key = os.environ["BINANCE_API_KEY"]
    api_secret = os.environ["BINANCE_API_SECRET"]

    spy = MiniSpy(api_key, api_secret)

    print("closing mini spy")
