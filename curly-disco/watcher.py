import asyncio
import json
import os
from datetime import datetime
from itertools import chain
from statistics import mean
from typing import Optional

import models
from binance.error import ClientError
from binance.spot import Spot
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient
from db import DB
from fastapi_utilities import repeat_at


class Watcher:
    def __init__(self, api_key=None, api_secret=None, spot: Optional[Spot] = None):
        self.client = spot if spot else Spot(api_key, api_secret)
        self.ws_client = SpotWebsocketStreamClient(on_message=self.on_message)

    def start_watch(self):
        listen_key = self.client.new_listen_key()["listenKey"]
        self.ws_client.user_data(listen_key=listen_key)

    def stop_watch(self):
        self.ws_client.stop()

    def on_message(self, _, msg: str):
        event = json.loads(msg)
        match event.get("e", ""):
            case "executionReport":
                asyncio.run(self.handle_execution_report(event))
            case "outboundAccountInfo":
                print(msg)
            case _:
                pass
        return True

    async def handle_execution_report(self, msg: dict):
        pair = msg["s"]
        token_qty = float(msg["q"])
        quote_qty = float(msg["Z"])
        base_unit_price = float(msg["L"])
        if msg["X"] != "FILLED":
            return
        print(f"on_message: {msg}")
        asset = await models.Assets().get_or_none(id=pair)
        print(f"Order: {msg['i']} {msg['S']} {pair} {token_qty} {quote_qty} {base_unit_price}")
        await models.Orders.create(
            id=msg["i"],
            pair=pair,
            side=msg["S"],
            base_unit_price=base_unit_price,
            token_quantity=float(msg["q"]),
            quote_quantity=float(msg["p"]) * float(msg["q"]),
            timestamp=datetime.fromtimestamp(msg["T"] / 1000),
        )

        if msg["S"] == "BUY":
            if asset:
                asset.update_from_dict(
                    {
                        "token_quantity": float(asset.token_quantity) + token_qty,
                        "quote_quantity": float(asset.quote_quantity) + quote_qty,
                        "market_value": (float(asset.token_quantity) + token_qty)
                        * (float(asset.quote_quantity) + quote_qty),
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
                await self.mitrailles(pair, base_unit_price)

        elif msg["S"] == "SELL":
            if asset:
                if float(asset.token_quantity) - token_qty < 0.0000001:
                    await asset.delete()
                else:
                    asset.update_from_dict(
                        {
                            "token_quantity": float(asset.token_quantity) - token_qty,
                            "quote_quantity": float(asset.quote_quantity) - quote_qty,
                        }
                    )
                await models.Trades.create(
                    id=msg["i"],
                    pair=pair,
                    opened_at=asset.opened_at,
                    closed_at=datetime.fromtimestamp(msg["T"] / 1000),
                    token_quantity=token_qty,
                    buy_unit_price=asset.buy_unit_price,
                    buy_quote_quantity=asset.quote_quantity,
                    sell_unit_price=base_unit_price,
                    sell_quote_quantity=quote_qty,
                    gains=quote_qty - float(asset.quote_quantity),
                    gains_percentage=((quote_qty - float(asset.quote_quantity)) / float(asset.quote_quantity)) * 100,
                )
            pass
        else:
            pass
        return True

    async def mitrailles(self, pair: str, start_price: float):
        mitraille_range = float((await models.Settings.get(key=models.Settings.Keys.MITRAILLE_PERCENTAGE)).value) / 100
        mitraille_quantity = int((await models.Settings.get(key=models.Settings.Keys.MITRAILLE_QUANTITY)).value)
        quantity = float((await models.Settings.get(key=models.Settings.Keys.BUY_AMOUNT)).value)
        asset_detail = await models.Market.get(pair=pair)
        for index in range(1, mitraille_quantity + 1):
            target_price = (
                (start_price - (start_price * (index / mitraille_quantity) * mitraille_range))
                // float(asset_detail.tick_price)
                * float(asset_detail.tick_price)
            )
            buy_quantity = (
                (quantity / target_price) // float(asset_detail.tick_quantity) * float(asset_detail.tick_quantity)
            )
            try:
                self.client.new_order(
                    symbol=pair,
                    side="BUY",
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=(format(round(buy_quantity, 8), "g")),
                    price=(format(round(target_price, 8), "g")),
                )

            except ClientError as e:
                if e.error_code == -2010 and "insufficient balance" in e.error_message:
                    print("Insufficient balance")
                    break
                else:
                    print(f"Order Refused: {pair} code={e.error_code}, message={e.error_message}")

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
        pairs_to_skip = await models.Assets.all().values_list("id", flat=True)
        pairs = _pairs if _pairs else [x.pair for x in market]
        # Remove pairs that are already in the assets
        [pairs.remove(x) for x in pairs_to_skip if x in pairs]
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
            if moving_delta < threshold:
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

    @repeat_at(cron="1 0 * * *")  # every day 00:01
    def loop_entries(self):
        asyncio.run(self.strat_loop_compute_entry())

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

    async def update_assets_gains(self):
        assets = await models.Assets().all()
        if assets:
            prices = await self.pairs_to_prices([x.id for x in assets])
            for asset in assets:
                asset.market_value = float(asset.token_quantity) * prices[asset.id]
                asset.market_unit_price = prices[asset.id]
                asset.gains = asset.market_value - float(asset.quote_quantity)
                asset.gains_percentage = (asset.gains / float(asset.quote_quantity)) * 100
            await models.Assets.bulk_update(
                assets, fields=["market_value", "market_unit_price", "gains", "gains_percentage", "updated_at"]
            )

    @repeat_at(cron="*/5 * * * *")
    def loop_exit(self):
        asyncio.run(self.strat_loop_compute_exit())

    async def strat_loop_compute_exit(self):
        print(f"Strat loop exit {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await self.update_assets_gains()
        await self.delist_exit()
        open_orders = list(filter(lambda x: x["side"] == "SELL", self.client.get_open_orders()))

        assets = await models.Assets().all()
        sell_gains_percentage = float((await models.Settings.get(key=models.Settings.Keys.SELL_GAINS_PERCENTAGE)).value)
        sell_trailing_stop = int((await models.Settings.get(key=models.Settings.Keys.SELL_TRAILING_STOP)).value) * 100
        for asset in assets:
            sell_orders = list(filter(lambda x: x["symbol"] == asset.id, open_orders))
            print(f"Checking exit for {asset.id} {asset.gains_percentage}")
            if asset.gains_percentage >= sell_gains_percentage and not sell_orders:
                try:
                    self.client.new_order(
                        symbol=asset.id,
                        side="SELL",
                        type="TAKE_PROFIT",
                        quantity=asset.token_quantity,
                        trailingDelta=sell_trailing_stop,
                    )
                except ClientError as e:
                    print(f"Order Refused: {asset.id} code={e.error_code}, message={e.error_message}")
                except Exception as e:
                    print(f"Error on placing order for {asset.id}: {e}")
        return True

    async def delist_exit(self):
        delist = self.client.delist_schedule_symbols()
        if not delist:
            return
        symbols = list(chain(*list(map(lambda x: x["symbols"], delist))))
        for symbol in symbols:
            if market := await models.Market.get_or_none(pair=symbol):
                market.is_black_listed = True
                await market.save()
            try:
                self.client.cancel_open_orders(symbol=symbol)
            except ClientError as err:
                print(f"Delist: Failed to cancel orders on {symbol}.{err.error_code} {err.error_message}")
            if asset := await models.Assets.get_or_none(id=symbol):
                try:
                    self.client.new_order(
                        symbol=symbol,
                        side="SELL",
                        type="MARKET",
                        quantity=asset.token_quantity,
                    )
                    print(f"Delist: emergency sell on {symbol}")
                except ClientError as err:
                    print(f"Delist: Failed to sell on {symbol}.{err.error_code} {err.error_message}")


if __name__ == "__main__":
    asyncio.run(DB.init())

    watcher = Watcher(api_key=os.environ["BINANCE_API_KEY"], api_secret=os.environ["BINANCE_API_SECRET"])

    data = asyncio.run(watcher.strat_compute_entry())
    with open("data.json", "w") as f:
        for d in data:
            f.write(str(d) + "\n")
    watcher.ws_client.stop()
    asyncio.run(DB.close())
