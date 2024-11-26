from datetime import datetime
from typing import Iterable

import models
from binance.spot import Spot


class Bot:
    def __init__(self, api_key, api_secret):
        self.client = Spot(api_key, api_secret)

    def get_assets(self):
        """_summary_
        Returns:
            array[dict]: [{'asset': 'BNB', 'free': '0.00000170', 'locked': '0.00000000'}]
        """
        return self.client.account(omitZeroBalances="true").get("balances")

    def get_trades(self, pair):
        """_summary_

        Args:
            symbol (str): pair to get trades for (e.g. "ENJUSDT")

        Returns:
        """
        return self.client.my_trades(symbol=pair)

    async def init_trades_history(self, pairs: Iterable[str]):
        for pair in pairs:
            print(f"Fetching trades for {pair}")
            data = list(
                map(
                    lambda x: models.TradesHistory(
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
            await models.TradesHistory.bulk_create(
                data, on_conflict=["id"], ignore_conflicts=True
            )

    async def init_tradable_pairs(self):
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

        pairs: list[str] = await models.TradablePairs.all().values_list(
            "symbol", flat=True
        )  # type: ignore
        await self.init_trades_history(pairs)

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
        api_key=os.environ["API_KEY_READONLY"],
        api_secret=os.environ["API_SECRET_READONLY"],
    )

    asyncio.run(bot.first_run())
    asyncio.run(DB.close())
