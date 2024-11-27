from tortoise import fields, models


class OrdersHistory(models.Model):
    """Model to store trades history as-it from Binance API"""

    id = fields.IntField(pk=True)
    pair = fields.CharField(max_length=20)
    timestamp = fields.DatetimeField()
    side = fields.CharField(max_length=10)
    unitPrice = fields.DecimalField(10, 10)
    tokenQuantity = fields.DecimalField(10, 10)
    usdtQuantity = fields.DecimalField(10, 10)

    def __repr__(self) -> str:
        return f"{self.pair} {self.timestamp} {self.side} {self.tokenQuantity} {self.unitPrice} {self.usdtQuantity}"


class TradesHistory(models.Model):
    """Model to store trades history as-it from Binance API"""

    id = fields.IntField(pk=True)
    pair = fields.CharField(max_length=20)
    openTimestamp = fields.DatetimeField()
    closeTimestamp = fields.DatetimeField()
    tokenTotalQuantity = fields.DecimalField(10, 10)
    buyUsdtTotalQuantity = fields.DecimalField(10, 10)
    buyUnitPrice = fields.DecimalField(10, 10)
    sellUsdtTotalQuantity = fields.DecimalField(10, 10)
    sellUnitPrice = fields.DecimalField(10, 10)


class Assets(models.Model):
    """Store the current wallet situation to avoid.
    As we are going to use the websocket API, and the REST API is lagging behind"""

    symbol = fields.CharField(max_length=20, pk=True)
    asset = fields.CharField(max_length=10)
    quantity = fields.DecimalField(10, 10)
    valuation = fields.DecimalField(10, 10)
    createdAt = fields.DatetimeField(auto_now_add=True)
    updatedAt = fields.DatetimeField(auto_now=True)


class TradablePairs(models.Model):
    """Store the tradable pairs to avoid querying the API every time.
    And will be used to blacklist some pairs that we dont want to trade on.
    """

    symbol = fields.CharField(max_length=20, pk=True)
    asset = fields.CharField(max_length=10)
    quoteAsset = fields.CharField(max_length=10)
    isBlacklisted = fields.BooleanField(default=False)
    createdAt = fields.DatetimeField(auto_now_add=True)
    updatedAt = fields.DatetimeField(auto_now=True)


class Settings(models.Model):
    key = fields.CharField(max_length=250, pk=True)
    value = fields.CharField(max_length=250)
    updatedAt = fields.DatetimeField(auto_now=True)
