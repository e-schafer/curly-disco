import asyncio
import os
from datetime import datetime
from statistics import mean

import models
from binance.error import ClientError
from binance.spot import Spot
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient
from db import DB
from fastapi_utilities import repeat_every


class Watcher:
    def __init__(self, api_key, api_secret):
        self.client: Spot = Spot(api_key, api_secret)

        self.ws_client = SpotWebsocketStreamClient(
            on_message=self.on_message, stream_url="wss://stream.testnet.binance.vision:9443/ws"
        )
        self.listen_key = self.client.new_listen_key()

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

        asset = await models.Assets().get(id=pair)
        if msg["S"] == "BUY":
            token_qty = float(msg["q"])
            quote_qty = float(msg["p"])
            asset = await models.Assets().get(id=pair)
            if asset:
                asset.update_from_dict(
                    {
                        "token_quantity": float(asset.token_quantity) + token_qty,
                        "quote_quantity": float(asset.quote_quantity) + quote_qty,
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
        print(f"Bitcoin variation: {bitcoin_variation}")
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
        print(f"Lessper: {lessper}")
        return lessper / 100

    async def cancel_buy_orders(self):
        orders = self.client.get_open_orders()
        pairs_mitrailles = await models.Assets.all().values_list("id", flat=True)
        for order in orders:
            if order["side"] == "BUY" and order["symbol"] not in pairs_mitrailles:
                self.client.cancel_open_orders(symbol=order["symbol"])

    async def strat_compute_entry(self, _pairs: list[str] = []) -> list[dict]:
        print("Computing entries")
        threshold = float((await models.Settings.get(key=models.Settings.Keys.WEEKLY_DEVIATION_PERCENTAGE)).value) / 100
        buy_amount = float((await models.Settings.get(key=models.Settings.Keys.BUY_AMOUNT)).value)
        market = await models.Market.filter(is_black_listed=False).all()
        pairs = _pairs if _pairs else [x.pair for x in market]

        lessper = await self.get_lessper()
        positions = []

        for index, pair in enumerate(pairs):
            print(f"Computing entry for {pair} ({index + 1}/{len(pairs)})")
            ticks = self.client.ui_klines(symbol=pair, interval="1d", limit=8)
            if len(ticks) < 7:
                continue
            moving_average = list(map(lambda x: (float(x[2]) + float(x[3])) / 2, ticks[:-1]))
            moving_delta = (max(moving_average) / min(moving_average)) - 1
            asset = [x for x in market if x.pair == pair][0]
            if moving_delta < float(threshold):
                positions.append(
                    {
                        "pair": pair,
                        "delta": moving_delta * 100,
                        "mean": (avg := mean(moving_average)),
                        "current_price": (current_price := float(ticks[-1][4])),
                        "target_price": (
                            target_price := ((avg * (1 - lessper)) // float(asset.tick_price)) * float(asset.tick_price)
                        ),
                        "far": ((current_price / target_price) - 1) * 100,
                        "quantity": ((buy_amount / target_price) // float(asset.tick_quantity))
                        * float(asset.tick_quantity),
                    }
                )
        positions.sort(key=lambda x: x["far"])
        return positions

    @repeat_every(seconds=60 * 60 * 24)  # 24 hours
    async def strat_loop_compute_entry(self, pairs: list[str] = []):
        print(f"Strat loop {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await self.cancel_buy_orders()
        entries = await self.strat_compute_entry(pairs)
        for entry in entries:
            try:
                print(
                    f"TRY Order: {entry['pair']}, qty={format(round(entry["quantity"], 8), "g")}, target_price={format(round(entry["target_price"], 8), "g")}, current_price={format(round(entry["current_price"], 8), "g")}"
                )
                self.client.new_order(
                    symbol=entry["pair"],
                    side="BUY",
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=(format(round(entry["quantity"], 8), "g")),
                    price=(format(round(entry["target_price"], 8), "g")),
                )

            except ClientError as e:
                if e.error_code == -2010 and "insufficient balance" in e.error_message:
                    print("Insufficient balance")
                    break
                else:
                    print(f"Order Refused: {entry['pair']} code={e.error_code}, message={e.error_message}")

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
        opened_orders = []
        if orders:
            prices = await self.pairs_to_prices([x["symbol"] for x in orders])
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

    async def update_assets_gains(self):
        assets = await models.Assets().all()
        if assets:
            prices = await self.pairs_to_prices([x.id for x in assets])
            for asset in assets:
                asset.market_value = float(asset.token_quantity) * prices[asset.id]
                asset.gains = asset.market_value - float(asset.quote_quantity)
                asset.gains_percentage = (asset.gains / float(asset.quote_quantity)) * 100
            await models.Assets.bulk_update(assets, fields=["market_value", "gains", "gains_percentage", "updated_at"])

    @repeat_every(seconds=60 * 5)  # 5 minutes
    async def strat_loop_compute_exit(self):
        print(f"Strat loop exit {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await self.update_assets_gains()
        assets = await models.Assets().all()
        sell_gains_percentage = float((await models.Settings.get(key=models.Settings.Keys.SELL_GAINS_PERCENTAGE)).value)
        sell_trailing_stop = float((await models.Settings.get(key=models.Settings.Keys.SELL_TRAILING_STOP)).value)
        for asset in assets:
            print(f"Checking exit for {asset.id} {asset.gains_percentage}")
            if asset.gains_percentage >= sell_gains_percentage:
                try:
                    self.client.new_order(
                        symbol=asset.id,
                        side="SELL",
                        type="TAKE_PROFIT",
                        timeInForce="GTC",
                        quantity=asset.token_quantity,
                        trailingDelta=sell_trailing_stop,
                    )
                except ClientError as e:
                    print(f"Order Refused: {asset.id} code={e.error_code}, message={e.error_message}")


if __name__ == "__main__":
    asyncio.run(DB.init())

    watcher = Watcher(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])

    asyncio.run(watcher.strat_loop_compute_entry())

    asyncio.run(DB.close())
    asyncio.run(DB.close())
