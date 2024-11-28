import time
from datetime import datetime
from itertools import accumulate, groupby
from signal import siginterrupt

import models
from binance.spot import Spot


class Bot:
    def __init__(self, api_key, api_secret):
        self.client = Spot(api_key, api_secret)

    async def init_trades_history(self):
        pairs = list(
            map(
                lambda x: x["symbol"],
                list(
                    filter(
                        lambda y: y["quoteAsset"] == "USDT",
                        self.client.exchange_info(permissions=["SPOT"]).get("symbols"),
                    )
                ),
            )
        )
        for pair in pairs:
            print(f"Fetching trades for {pair}")
            data = list(
                map(
                    lambda x: models.OrdersHistory(
                        id=x["id"],
                        pair=x["symbol"],
                        side="BUY" if x["isBuyer"] else "SELL",
                        unitPrice=x["price"],
                        tokenQuantity=x["qty"],
                        usdtQuantity=x["quoteQty"],
                        timestamp=datetime.fromtimestamp(x["time"] / 1000),
                    ),
                    self.client.my_trades(symbol=pair),
                )
            )
            await models.OrdersHistory.bulk_create(
                data, on_conflict=["id"], ignore_conflicts=True
            )

    async def init_tradable_pairs(self):
        print("Fetching tradable pairs")
        data = list(
            map(
                lambda y: models.TradablePairs(
                    symbol=y["symbol"],
                    asset=y["baseAsset"],
                    quoteAsset=y["quoteAsset"],
                ),
                filter(
                    lambda x: x["quoteAsset"] == "USDT"
                    and x["allowTrailingStop"]
                    and x["isSpotTradingAllowed"]
                    and x["status"] == "TRADING",
                    self.client.exchange_info(permissions=["SPOT"]).get("symbols"),
                ),
            )
        )
        await models.TradablePairs.bulk_create(
            data, on_conflict=["symbol"], ignore_conflicts=True
        )

    async def first_run(self):
        await self.init_tradable_pairs()
        await self.init_trades_history()

    def set_entry_point(self, pair, delta):
        raise NotImplementedError()

    def set_exit_point(self, pair, target, trailing_delta):
        raise NotImplementedError()

    async def sandbox(self):
        trades: list[models.OrdersHistory] = await models.OrdersHistory().filter(
            pair="ENJUSDT"
        )
        # pp(trades)
        # print("---------------")
        # merge each group of orders into a single order

        for key, group in groupby(
            trades,
            lambda x: (
                x.pair,
                x.side,
                x.timestamp,
            ),
        ):
            pp(list(group))
            models.OrdersHistory(
                id=0,
                pair=key[0],
                timestamp=key[1],
                side=key[2],
                tokenQuantity=sum([x.tokenQuantity for x in group]),
                usdtQuantity=sum([x.usdtQuantity for x in group]),
            )

        # parcourd merged to calculate the profit. after each sell order, the profit is calculated
        # and a models.TradesHistory is created. before a sell order we need accumulate all the buy orders
        # quantity = 0
        # quote_quantity = 0
        # orders: list[models.TradesHistory] = []
        # first_timestamp = datetime(1970, 1, 1)
        # side = "sell"
        # for order in merged:
        #     if order.side == "BUY":
        #         quantity += order.tokenQuantity
        #         quote_quantity += order.usdtQuantity
        #         if side == "sell":
        #             first_timestamp = order.timestamp
        #             side = "buy"
        #     else:
        #         orders.append(
        #             models.TradesHistory(
        #                 pair=order.pair,
        #                 openTimestamp=first_timestamp,
        #                 closeTimestamp=order.timestamp,
        #                 tokenTotalQuantity=quantity,
        #                 buyUsdtTotalQuantity=quote_quantity,
        #                 buyUnitPrice=quote_quantity / quantity,
        #                 sellUsdtTotalQuantity=order.usdtQuantity,
        #                 sellUnitPrice=order.usdtQuantity / order.tokenQuantity,
        #             )
        #         )
        #         side = "sell"
        #         quantity = 0
        #         quote_quantity = 0
        # pp(orders)


if __name__ == "__main__":
    import asyncio
    import os
    from pprint import pp

    from db import DB

    asyncio.run(DB.init())

    bot = Bot(
        api_key=os.environ["API_KEY_WRITE"],
        api_secret=os.environ["API_SECRET_WRITE"],
    )
    asyncio.run(bot.sandbox())
    asyncio.run(DB.close())
