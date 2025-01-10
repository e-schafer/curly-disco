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

    async def init_orders_and_trades(self, selected_pairs: list[str] = []):
        await models.Orders.all().delete()
        await models.Trades.all().delete()
        pairs = (
            selected_pairs
            if selected_pairs
            else list(
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
        )

        for pair in pairs:
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
            print(f"Orders found {len(data)} for {pair}") if data else None
            await models.Orders.bulk_create(data, on_conflict=["id"], ignore_conflicts=True)
            await models.Trades.bulk_create(
                objects=await self.__init_trades_history(data),
                on_conflict=["pair", "opened_at", "closed_at"],
                ignore_conflicts=True,
            )

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
            if order.side == "BUY":
                BQuoteQuantity += order.quote_quantity
                Btoken_quantity += order.token_quantity
                if opened_at == datetime(1970, 1, 1):
                    opened_at = order.timestamp
            else:
                trades.append(
                    models.Trades(
                        id=order.id,
                        pair=order.pair,
                        opened_at=opened_at,
                        closed_at=order.timestamp,
                        token_quantity=order.token_quantity,
                        buy_unit_price=Btoken_quantity / BQuoteQuantity,
                        buy_quote_quantity=BQuoteQuantity,
                        sell_unit_price=order.base_unit_price,
                        sell_quote_quantity=order.quote_quantity,
                        gains=order.quote_quantity - BQuoteQuantity,
                        gains_percentage=(
                            ((order.quote_quantity / BQuoteQuantity) - 1) * 100 if BQuoteQuantity != 0 else 0
                        ),
                    ),
                )
                BQuoteQuantity = 0
                Btoken_quantity = 0
                opened_at = datetime(1970, 1, 1)
        return trades

    async def init_market(self):
        """_summary_"""

        def extract_filters(filters: list[dict]):
            filterPrice = list(filter(lambda x: x["filterType"] == "PRICE_FILTER", filters))[0]
            filterQuantity = list(filter(lambda x: x["filterType"] == "LOT_SIZE", filters))[0]
            return {
                "min_price": float(filterPrice["minPrice"]),
                "tick_price": float(filterPrice["tickSize"]),
                "min_quantity": float(filterQuantity["minQty"]),
                "tick_quantity": float(filterQuantity["stepSize"]),
            }

        await models.Market.all().delete()
        data = list(
            map(
                lambda y: models.Market(
                    pair=y["symbol"],
                    symbol=y["baseAsset"],
                    quote_symbol=y["quoteAsset"],
                    **extract_filters(y["filters"]),
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
        print(f"Market found {len(data)} pairs")
        await models.Market.bulk_create(data, on_conflict=["symbol"], ignore_conflicts=True)

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
                buy_unit_price=quote_quantity / token_quantity,
                market_value=token_quantity * current_unit_price,
                market_unit_price=current_unit_price,
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
        api_key=os.environ["BINANCE_API_KEY"],
        api_secret=os.environ["BINANCE_API_SECRET"],
    )
    asyncio.run(bot.init_assets())

    asyncio.run(DB.close())
