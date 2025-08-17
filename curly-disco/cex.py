from abc import ABC, abstractmethod

import models
import tortoise.functions as tf
from binance.spot import Spot


class ExchangeInterface(ABC):
    NUMBER_OF_ITEMS = 20

    def __init__(self, api_key, api_secret):
        self.client = Spot(api_key, api_secret)

    @abstractmethod
    async def render(self):
        pass

    async def pairs_to_prices(self, pairs: list[str]) -> dict:
        prices = dict(
            map(
                lambda x: (x["symbol"], float(x["price"])),
                self.client.ticker_price(symbols=pairs),
            )
        )
        return prices

    async def get_liquidity(self):
        liquidity = {
            "locked": 0.0,
            "free": 0.0,
            "bought": 0.0,
            "market_value": 0.0,
            "total_gains": 0.0,
        }
        asset = (
            await models.Assets.annotate(
                crypto_bought=tf.Coalesce(tf.Sum("quote_quantity"), 0.0),
                market_value=tf.Coalesce(tf.Sum("market_value"), 0.0),
            )
            .first()
            .values()
        )
        trades = await models.Trades.annotate(gains=tf.Sum("gains")).first().values()
        if trades:
            liquidity["total_gains"] = float(trades["gains"] if trades["gains"] else 0)
        liquidity["bought"] = float(asset["crypto_bought"])
        liquidity["market_value"] = float(asset["market_value"]) + liquidity["free"] + liquidity["locked"]
        if usdt := self.client.user_asset(asset="USDT"):
            liquidity["locked"] = float(usdt[0]["locked"])
            liquidity["free"] = float(usdt[0]["free"])
        return liquidity

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
