import os
from datetime import datetime
from pprint import pp
from typing import Optional

import models
from binance.spot import Spot
from utils.logger import log_api


class InitDB:
    def __init__(self, api_key=None, api_secret=None, spot: Optional[Spot] = None):
        self.client = spot if spot else Spot(api_key, api_secret)

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
            if data:
                log_api("info", f"Found {len(data)} orders for {pair}", endpoint="get_orders")
            await models.Orders.bulk_create(data, on_conflict=["id"], ignore_conflicts=True)
            await models.Trades.bulk_create(
                objects=await self.__init_token_trades(data),
                on_conflict=["pair", "opened_at", "closed_at"],
                ignore_conflicts=True,
            )

    async def __init_token_trades(self, orders: list[models.Orders]) -> list[models.Trades]:
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

    async def check_market_table(self):
        nbr = await models.Assets.all().count()
        if nbr == 0:
            self.init_market()

    def init_market(self):
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

        def is_history_long_enough(pair: str):
            klines = self.client.klines(symbol=pair, interval="1M", limit="7")
            return True if len(klines) >= 6 else False

        data = list(
            filter(
                lambda x: x["quoteAsset"] == "USDT"
                and x["baseAsset"] not in ("USDT", "TUSD", "USDC", "USDP")
                and x["allowTrailingStop"]
                and x["isSpotTradingAllowed"]
                and x["status"] == "TRADING",
                self.client.exchange_info(permissions=["SPOT"]).get("symbols"),
            )
        )
        log_api("info", f"Market info: {len(data)} pairs available", endpoint="exchange_info")
        data = list(filter(lambda z: is_history_long_enough(z["symbol"]), data))
        log_api("info", f"Market filter: {len(data)} pairs accepted after history check", endpoint="ui_klines")
        data = list(
            map(
                lambda y: models.Market(
                    pair=y["symbol"],
                    symbol=y["baseAsset"],
                    quote_symbol=y["quoteAsset"],
                    **extract_filters(y["filters"]),
                ),
                data,
            )
        )
        models.Market.all().delete()
        models.Market.bulk_create(data, on_conflict=["symbol"], ignore_conflicts=True)

    async def init_assets(self):
        async def compute_asset(pair: str):
            log_api("debug", f"Fetching trades for asset {pair}", endpoint="get_orders")
            data = self.client.get_orders(symbol=pair)
            orders = list(filter(lambda x: x["status"] == "FILLED", data))
            orders.sort(key=lambda x: x["time"], reverse=True)
            token_quantity: float = 0.0
            quote_quantity: float = 0.0
            opened_at: datetime = datetime(1970, 1, 1)
            for index, order in enumerate(orders):
                if order["side"] == "SELL":
                    # in this case we have asset but the last order is SELL
                    # which means we have dust to collect
                    if index == 0:
                        resp = self.client.transfer_dust([pair.replace("USDT", "")])
                        log_api(
                            "info", f"Dust transfer result: {resp.get('transferResult', '')}", endpoint="transfer_dust"
                        )
                        return
                    # we reach last sell operation and we can guess we have all BUY orders
                    else:
                        break
                token_quantity += float(order.get("origQty", 0))
                quote_quantity += float(order.get("cummulativeQuoteQty", 0))
                opened_at = datetime.fromtimestamp(order["time"] / 1000)

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
            await compute_asset(pair)

    async def init_settings(self):
        """Initialize settings with default values if they don't exist"""
        default_settings = {
            models.Settings.Keys.SELL_GAINS_PERCENTAGE: 20,
            models.Settings.Keys.SELL_TRAILING_STOP: 5,
            models.Settings.Keys.WEEKLY_DEVIATION_PERCENTAGE: 69,
            models.Settings.Keys.BUY_AMOUNT: 20,
            models.Settings.Keys.MITRAILLE_PERCENTAGE: 20,
            models.Settings.Keys.MITRAILLE_QUANTITY: 20,
            models.Settings.Keys.LESSPER_DEFAULT: 20,
        }

        # Check existing settings to avoid conflicts
        existing_keys = set(await models.Settings.all().values_list("key", flat=True))

        settings_to_create = [
            models.Settings(key=key, value=value) for key, value in default_settings.items() if key not in existing_keys
        ]

        if settings_to_create:
            await models.Settings.bulk_create(settings_to_create)
            log_api("info", f"Created {len(settings_to_create)} default settings", endpoint="init_settings")

    async def first_run(self):
        # await self.init_settings()
        # await self.init_market()
        # await self.init_orders_and_trades()
        await self.init_assets()


if __name__ == "__main__":
    import asyncio

    from db import DB

    asyncio.run(DB.init())

    bot = InitDB(
        api_key=os.environ["BINANCE_API_KEY"],
        api_secret=os.environ["BINANCE_API_SECRET"],
    )
    asyncio.run(bot.first_run())

    asyncio.run(DB.close())
