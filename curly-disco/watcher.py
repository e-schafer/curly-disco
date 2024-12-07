import os
from datetime import datetime
from pprint import pp
from statistics import mean

import models
from binance.spot import Spot
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient


class Watcher:
    def __init__(self, api_key, api_secret):
        self.client: Spot = Spot(api_key, api_secret)
        # self.ws_client = SpotWebsocketStreamClient(
        #     on_message=self.on_message, stream_url="wss://stream.testnet.binance.vision:9443/ws"
        # )
        # self.listen_key = self.client.new_listen_key()

    async def start(self):
        pass

    async def stop(self):
        pass

    async def on_message(self, msg):
        match msg["e"]:
            case "executionReport":
                await self.handle_execution_report(msg)
            case "outboundAccountInfo":
                print(msg)
            case _:
                pass

    async def handle_execution_report(self, msg):
        pair = msg["s"]

        symbol = await models.Assets().get(id=pair)
        if msg["S"] == "BUY":
            token_qty = float(msg["q"])
            quote_qty = float(msg["p"])
            symbol = await models.Assets().get(id=pair)
            if symbol:
                symbol.update_from_dict(
                    {
                        "token_quantity": float(symbol.token_quantity) + token_qty,
                        "quote_quantity": float(symbol.quote_quantity) + quote_qty,
                    }
                )
            else:
                await models.Assets.create(
                    id=pair,
                    token_quantity=token_qty,
                    quote_quantity=quote_qty,
                    market_value=token_qty * quote_qty,
                    opened_at=datetime.fromtimestamp(msg["T"] / 1000),
                )
                # trigger mitraille order

        elif msg["S"] == "SELL":
            # TODO
            pass
        else:
            pass

    async def get_lessper(self):
        lessper = float((await models.Settings.get(key=models.Settings.Keys.LESSPER_DEFAULT)).value)
        bitcoin_variation = float(self.client.ticker_24hr(symbol="BTCUSDT")["priceChangePercent"])
        if bitcoin_variation >= -2.5:
            lessper += 2.5
        elif bitcoin_variation >= -4.5:
            lessper += 5
        elif bitcoin_variation >= -7.5:
            lessper += 10
        elif bitcoin_variation >= -9.5:
            lessper += 15
        elif bitcoin_variation >= -13:
            lessper += 20
        elif bitcoin_variation >= -16:
            lessper += 25
        elif bitcoin_variation >= -20:
            lessper += 30
        else:
            lessper += 35
        return lessper

    async def put_order(self):
        threshold = float((await models.Settings.get(key=models.Settings.Keys.WEEKLY_DEVIATION_PERCENTAGE)).value)
        buy_amount = float((await models.Settings.get(key=models.Settings.Keys.BUY_AMOUNT)).value)
        pairs = [x["pair"] for x in await models.Market.filter(is_black_listed=False).values("pair")]
        lessper = await self.get_lessper()
        positions = []
        for pair in pairs:
            ticks = self.client.ui_klines(symbol=pair, interval="1d", limit=8)
            moving_average = list(map(lambda x: float(x[2]) + float(x[3]) / 2, ticks))
            moving_delta = (max(moving_average) / min(moving_average)) - 1

            if moving_delta < float(threshold) / 100:
                positions.append(
                    {
                        "pair": pair,
                        "delta": moving_delta * 100,
                        "current_price": float(ticks[-1][4]),
                        "target_price": mean(moving_average) * (1 - lessper),
                        "far": (float(ticks[-1][4]) / mean(moving_average)) * 100,
                        "quantity": buy_amount / float(ticks[-1][4]),
                    }
                )
        positions.sort(key=lambda x: x["far"])
        return positions

    async def pairs_to_prices(self, pairs: list[str]) -> dict:
        prices = dict(
            map(
                lambda x: (x["symbol"], float(x["price"])),
                self.client.ticker_price(symbols=pairs),
            )
        )
        return prices

    async def get_opened_buy_orders(self) -> list[dict]:
        orders = self.client.get_open_orders()
        prices = await self.pairs_to_prices([x["symbol"] for x in orders])
        opened_orders = []
        for order in orders:
            opened_orders.append(
                {
                    "pair": order["symbol"],
                    "quantity": order["origQty"],
                    "target_price": (target_price := float(order["price"])),
                    "current_price": (current_price := prices[order["symbol"]]),
                    "far": ((float(current_price) / target_price) - 1) * 100,
                }
            )
        return opened_orders

    async def get_upto_date_asset(self):
        assets = await models.Assets().all()
        prices = await self.pairs_to_prices([x.id for x in assets])
        for asset in assets:
            asset.market_value = float(asset.token_quantity) * prices[asset.id]
            asset.gains = asset.market_value - float(asset.quote_quantity)
            asset.gains_percentage = (asset.gains / float(asset.quote_quantity)) * 100
        await models.Assets.bulk_update(assets, fields=["market_value", "gains", "gains_percentage", "updated_at"])
        return await models.Assets().all().values()


if __name__ == "__main__":
    import asyncio

    from db import DB

    asyncio.run(DB.init())

    watcher = Watcher(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])
    pp(watcher.client.ticker_24hr(symbol="BTCUSDT"))
    # pp(asyncio.run())

    asyncio.run(DB.close())

    # asyncio.run(watcher.start())
    # asyncio.run(watcher.stop())
