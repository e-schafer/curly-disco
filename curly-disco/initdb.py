import os
from datetime import datetime
from pprint import pp

import models
from binance.spot import Spot


class InitDB:
    def __init__(self, api_key, api_secret):
        self.client = Spot(
            api_key,
            api_secret,
        )

    async def init_orders_and_trades(self):
        await models.Orders.all().delete()
        await models.Trades.all().delete()
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
            print(f"Fetching orders for {pair}")
            data = list(
                map(
                    lambda x: models.Orders(
                        id=x["orderId"],
                        pair=x["symbol"],
                        side=x["side"],
                        base_unit_price=x["price"],
                        token_quantity=x["origQty"],
                        quote_quantity=x["cummulativeQuoteQty"],
                        timestamp=datetime.fromtimestamp(x["time"] / 1000),
                    ),
                    list(filter(lambda x: x["status"] == "FILLED", self.client.get_orders(symbol=pair))),
                )
            )
            await models.Orders.bulk_create(data, on_conflict=["id"], ignore_conflicts=True)
            await models.Trades.bulk_create(
                objects=await self.__init_trades_history(data),
                on_conflict=["pair", "opened_at", "closed_at"],
                ignore_conflicts=True,
            )

    async def init_market(self):
        """_summary_"""
        await models.Market.all().delete()
        print("Fetching tradable pairs")
        data = list(
            map(
                lambda y: models.Market(
                    pair=y["symbol"],
                    symbol=y["baseAsset"],
                    quote_symbol=y["quoteAsset"],
                ),
                filter(
                    lambda x: x["quoteAsset"] == "USDT"
                    and x["baseAsset"] not in ("USDT", "TUSD", "USDC", "USDP")
                    and x["allowTrailingStop"]
                    and x["isSpotTradingAllowed"]
                    and x["status"] == "TRADING",
                    self.client.exchange_info(permissions=["SPOT"]).get("symbols"),
                ),
            )
        )
        await models.Market.bulk_create(data, on_conflict=["symbol"], ignore_conflicts=True)

    async def __init_trades_history(self, orders: list[models.Orders]) -> list[models.Trades]:
        """_summary_

        Args:
            pair (str): _description_. ex "BTCUSDT".

        Returns:
            _type_: _description_
        """

        BQuoteQuantity = 0
        Btoken_quantity = 0
        opened_at = datetime(1970, 1, 1)
        trades: list[models.Trades] = list()
        orders.sort(key=lambda x: x.timestamp)

        for order in orders:
            print(order)
            if order.side == "BUY":
                BQuoteQuantity += order.quote_quantity
                Btoken_quantity += order.token_quantity
            else:
                trades.append(
                    models.Trades(
                        id=order.id,
                        pair=order.pair,
                        opened_at=opened_at,
                        closed_at=order.timestamp,
                        token_quantity=order.token_quantity,
                        quote_quantity=BQuoteQuantity,
                        sold_value=order.quote_quantity,
                        gains=order.quote_quantity - BQuoteQuantity,
                        gains_percentage=(
                            ((order.quote_quantity / BQuoteQuantity) - 1) * 100 if BQuoteQuantity != 0 else 0
                        ),
                    ),
                )
        return trades

    async def init_assets(self):
        await models.Assets.all().delete()
        pairs = list(
            map(
                lambda y: f"{y['asset']}USDT",
                filter(
                    lambda x: x["asset"] not in ("USDT", "BNB"),
                    self.client.account(omitZeroBalances="true").get("balances"),
                ),
            )
        )
        pp(pairs)
        for pair in pairs:
            print(f"Fetching open trades for {pair}")
            orders = list(filter(lambda x: x["status"] == "FILLED", self.client.get_orders(symbol=pair)))
            orders.sort(key=lambda x: x["time"], reverse=True)
            token_quantity: float = 0.0
            quote_quantity: float = 0.0
            opened_at: datetime = datetime(1970, 1, 1)
            for order in orders:
                if order["side"] == "SELL":
                    break
                token_quantity += float(order.get("origQty", 0))
                quote_quantity += float(order.get("cummulativeQuoteQty", 0))
                opened_at = datetime.fromtimestamp(order["time"] / 1000)

            pp(f"{pair} {token_quantity} {quote_quantity} {opened_at}")
            current_unit_price = float((self.client.ticker_price(pair))["price"])
            await models.Assets.create(
                id=pair,
                token_quantity=token_quantity,
                quote_quantity=quote_quantity,
                base_unit_price=quote_quantity / token_quantity,
                market_value=token_quantity * current_unit_price,
                gains=token_quantity * current_unit_price - quote_quantity,
                gains_percentage=((token_quantity * current_unit_price) / quote_quantity - 1) * 100,
                opened_at=opened_at,
            )

    async def init_settings(self):
        settings = [
            models.Settings(key=models.Settings.Keys.SELL_GAINS_PERCENTAGE, value=20),
            models.Settings(key=models.Settings.Keys.SELL_TRAILING_STOP, value=5),
            models.Settings(key=models.Settings.Keys.WEEKLY_DEVIATION_PERCENTAGE, value=69),
            models.Settings(key=models.Settings.Keys.BUY_AMOUNT, value=20),
            models.Settings(key=models.Settings.Keys.MITRAILLE_PERCENTAGE, value=20),
            models.Settings(key=models.Settings.Keys.MITRAILLE_QUANTITY, value=20),
            models.Settings(key=models.Settings.Keys.LESSPER_DEFAULT, value=20),
        ]
        await models.Settings.bulk_create(settings, on_conflict=["key"], ignore_conflicts=True)

    async def first_run(self):
        await self.init_settings()
        await self.init_market()
        await self.init_orders_and_trades()
        await self.init_assets()


if __name__ == "__main__":
    import asyncio

    from db import DB

    asyncio.run(DB.init())

    bot = InitDB(
        api_key=os.environ["API_KEY_WRITE"],
        api_secret=os.environ["API_SECRET_WRITE"],
    )
    trades = asyncio.run(bot.first_run())
    pp(trades)
    asyncio.run(DB.close())
