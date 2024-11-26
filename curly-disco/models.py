import time

from tortoise import fields, models


class TradesHistory(models.Model):
    id = fields.IntField(pk=True)
    pair = fields.CharField(max_length=20)
    timestamp = fields.DatetimeField()
    side = fields.CharField(max_length=10)
    unitPrice = fields.DecimalField(10, 10)
    tokenQuantity = fields.DecimalField(10, 10)
    usdtQuantity = fields.DecimalField(10, 10)

    def __repr__(self) -> str:
        return f"{self.pair} {self.timestamp} {self.side} {self.tokenQuantity} {self.unitPrice} {self.usdtQuantity}"


class Assets(models.Model):
    symbol = fields.CharField(max_length=20, pk=True)
    asset = fields.CharField(max_length=10)
    quantity = fields.DecimalField(10, 10)
    valuation = fields.DecimalField(10, 10)
    createdAt = fields.DatetimeField(auto_now_add=True)
    updatedAt = fields.DatetimeField(auto_now=True)


class TradablePairs(models.Model):
    symbol = fields.CharField(max_length=20, pk=True)
    asset = fields.CharField(max_length=10)
    quoteAsset = fields.CharField(max_length=10)
    createdAt = fields.DatetimeField(auto_now_add=True)
    updatedAt = fields.DatetimeField(auto_now=True)
