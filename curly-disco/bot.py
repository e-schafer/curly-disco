from datetime import datetime

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

    async def get_trades_from_orders(self, orders: list[models.OrdersHistory]):
        """use the orders list to calculate gains and losses. between BUY and SELL orders."""
        for order in orders:
            pass

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

    asyncio.run(bot.first_run())
    asyncio.run(DB.close())
