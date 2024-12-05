from enum import StrEnum

from tortoise import fields, models


class Orders(models.Model):
    """Model to store trades history as-it from Binance API"""

    id = fields.IntField(pk=True)
    pair = fields.CharField(max_length=20)
    timestamp = fields.DatetimeField()
    side = fields.CharField(max_length=10)
    base_unit_price = fields.DecimalField(10, 10)
    token_quantity = fields.DecimalField(10, 10)
    quote_quantity = fields.DecimalField(10, 10)

    def __repr__(self) -> str:
        return f"{self.pair} {self.timestamp} {self.side} {self.base_unit_price} {self.token_quantity} {self.quote_quantity}"

    @staticmethod
    def nicegui_repr():
        return [
            {"name": "ID", "label": "id", "field": "id", "sortable": True, "required": True},
            {"name": "Pair", "label": "pair", "field": "pair", "sortable": True, "required": True},
            {"name": "Timestamp", "label": "timestamp", "field": "timestamp", "sortable": True, "required": True},
            {"name": "Side", "label": "side", "field": "side", "required": True},
            {
                "name": "Unit Price",
                "label": "base_unit_price",
                "sortable": True,
                "field": "base_unit_price",
                "required": True,
            },
            {
                "name": "Token Quantity",
                "label": "token_quantity",
                "field": "token_quantity",
                "sortable": True,
                "required": True,
            },
            {
                "name": "USDT Quantity",
                "label": "quote_quantity",
                "field": "quote_quantity",
                "sortable": True,
                "required": True,
            },
        ]


class Trades(models.Model):
    """Model to store trades history as-it from Binance API"""

    id = fields.IntField(pk=True)
    pair = fields.CharField(max_length=20)
    opened_at = fields.DatetimeField()
    closed_at = fields.DatetimeField()
    token_quantity = fields.DecimalField(10, 10)
    quote_quantity = fields.DecimalField(10, 10)
    sold_value = fields.DecimalField(10, 10)
    gains = fields.DecimalField(10, 10)
    gains_percentage = fields.DecimalField(10, 10)

    def __repr__(self) -> str:
        return f"{self.pair} {self.opened_at} {self.closed_at} {self.token_quantity} {self.quote_quantity}  {self.sold_value} {self.gains} {self.gains_percentage} "

    @staticmethod
    def nicegui_repr():
        return [
            {"name": "id", "label": "ID", "field": "id", "required": True},
            {"name": "pair", "label": "Pair", "field": "pair", "sortable": True, "required": True},
            {"name": "opened_at", "label": "Open Timestamp", "field": "opened_at", "sortable": True},
            {"name": "closed_at", "label": "Close Timestamp", "field": "closed_at", "sortable": True},
            {"name": "token_quantity", "label": "Token Quantity", "field": "token_quantity", "sortable": True},
            {"name": "quote_quantity", "label": "Buy USDT Quantity", "field": "quote_quantity", "sortable": True},
            {"name": "sold_value", "label": "Sell USDT Quantity", "field": "sold_value", "sortable": True},
            {"name": "gains", "label": "Gains", "field": "gains", "sortable": True, "required": True},
            {"name": "gains_percentage", "label": "Gains Percentage", "field": "gains_percentage", "sortable": True},
        ]


class Assets(models.Model):
    """Store the current wallet situation to avoid.
    As we are going to use the websocket API, and the REST API is lagging behind"""

    id = fields.CharField(max_length=10, pk=True)
    token_quantity = fields.DecimalField(10, 10)
    quote_quantity = fields.DecimalField(10, 10)
    base_unit_price = fields.DecimalField(10, 10)
    market_value = fields.DecimalField(10, 10)
    gains = fields.DecimalField(10, 10)
    gains_percentage = fields.DecimalField(10, 10)
    opened_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __repr__(self) -> str:
        return f"{self.id} {self.token_quantity} {self.quote_quantity} {self.opened_at} {self.updated_at}"

    @staticmethod
    def nicegui_repr():
        return [
            {"name": "id", "label": "ID", "field": "id", "sortable": True, "required": True},
            {"name": "token_quantity", "label": "Token Quantity", "field": "token_quantity", "required": True},
            {"name": "quote_quantity", "label": "Buy USDT Quantity", "field": "quote_quantity", "sortable": True},
            {"name": "base_unit_price", "label": "Buy Unit Price", "field": "base_unit_price", "required": True},
            {"name": "market_value", "label": "Current USDT Value", "field": "market_value", "sortable": True},
            {"name": "gains", "label": "Current gains", "field": "gains", "sortable": True},
            {"name": "gains_percentage", "label": "Gains Percentage", "field": "gains_percentage", "sortable": True},
            {"name": "opened_at", "label": "Open Timestamp", "field": "opened_at", "sortable": True},
            {"name": "updated_at", "label": "Updated At", "field": "updated_at", "sortable": True, "required": True},
        ]


class Market(models.Model):
    """Store the tradable pairs to avoid querying the API every time.
    And will be used to blacklist some pairs that we dont want to trade on.
    """

    pair = fields.CharField(max_length=20, pk=True)
    symbol = fields.CharField(max_length=10)
    quote_symbol = fields.CharField(max_length=10)
    is_black_listed = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Settings(models.Model):
    key = fields.CharField(max_length=250, pk=True)
    value = fields.CharField(max_length=250)
    updated_at = fields.DatetimeField(auto_now=True)

    class Keys(StrEnum):
        SELL_GAINS_PERCENTAGE = "sell_gains_percentage"
        SELL_TRAILING_STOP = "sell_trailing_stop"
        WEEKLY_DEVIATION_PERCENTAGE = "weekly_deviation_percentage"
        BUY_AMOUNT = "buy_amount"
        MITRAILLE_QUANTITY = "mitraille_quantity"
        MITRAILLE_PERCENTAGE = "mitraille_percentage"

    @staticmethod
    async def get_settings(key: Keys):
        return await Settings.get_or_none(key=key)
