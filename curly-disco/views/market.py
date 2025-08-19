import os
from datetime import datetime

import plotly.graph_objects as go
import requests
from cex import ExchangeInterface
from nicegui import ui


class MarketView(ExchangeInterface):
    API_KEY = os.getenv("COINMARKETCAP_API_KEY", "bf1d73e6-955f-4f56-be53-5a3cd5286020")

    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)

    def human_format(self, num):
        num = float("{:.3g}".format(num))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        return "{}{}".format("{:f}".format(num).rstrip("0").rstrip("."), ["", "K", "M", "B", "T"][magnitude])

    async def __get_crypto_fear_greed_index(self):
        url = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical"
        headers = {"X-CMC_PRO_API_KEY": self.API_KEY, "Accept": "application/json"}
        response: requests.Response = requests.get(url=url, headers=headers, params={"limit": 8})
        data = response.json()
        return data["data"]

    async def __get_market_data(self):
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": self.API_KEY, "Accept": "application/json"}
        response: requests.Response = requests.get(url=url, headers=headers)
        data = response.json()
        return data["data"]

    async def __render_fear_greed_index(self):
        data = await self.__get_crypto_fear_greed_index()
        fig = go.Figure(
            go.Scatter(
                x=[datetime.fromtimestamp(int(x["timestamp"])) for x in data],
                y=[y["value"] for y in data],
            )
        )
        fig.update_layout(template="plotly_white", margin=dict(l=0, r=0, t=0, b=0))
        ui.plotly(fig).classes("w-400 h-80")

    async def __render_bitcoin_dominance(self, data):
        with ui.card().props("flat bordered"):
            ui.label("Bitcoin Dominance")
            with ui.row():
                with ui.column():
                    ui.label("BTC").tailwind.font_weight("bold").text_color("orange-500")
                    ui.label(f"{round(data['btc_dominance'],2)}%").classes("text-xl")
                    if (btc_variation := data["btc_dominance"] - data["btc_dominance_yesterday"]) > 0:
                        ui.label(f"↑ {round(btc_variation,2)}%").classes("text-positive")
                    else:
                        ui.label(f"↓ {round(btc_variation,2)}%").classes("text-negative")
                with ui.column():
                    ui.label("ETH").tailwind.font_weight("bold").text_color("blue-700")
                    ui.label(f"{round(data['eth_dominance'],2)}%").classes("text-xl")
                    if (eth_variation := data["eth_dominance"] - data["eth_dominance_yesterday"]) > 0:
                        ui.label(f"↑ {round(eth_variation,2)}%").classes("text-positive")
                    else:
                        ui.label(f"↓ {round(eth_variation,2)}%").classes("text-negative")
                with ui.column():
                    ui.label("Other").tailwind.font_weight("bold").text_color("gray-500")
                    other_dominance = 100 - data["btc_dominance"] - data["eth_dominance"]
                    other_dominance_yesterday = 100 - data["btc_dominance_yesterday"] - data["eth_dominance_yesterday"]
                    ui.label(f"{round(other_dominance,2)}%").classes("text-xl")
                    if (other_variation := other_dominance - other_dominance_yesterday) > 0:
                        ui.label(f"↑ {round(other_variation,2)}%").classes("text-positive")
                    else:
                        ui.label(f"↓ {round(other_variation,2)}%").classes("text-negative")

    async def __render_market_cap(self, data):
        total_cap = data["quote"]["USD"]["total_market_cap"]
        total_cap_yesterday = data["quote"]["USD"]["total_market_cap_yesterday"]
        alt_cap = data["quote"]["USD"]["total_market_cap"] * (100 - data["btc_dominance"]) / 100
        alt_cap_yesterday = (
            data["quote"]["USD"]["total_market_cap_yesterday"] * (100 - data["btc_dominance_yesterday"]) / 100
        )

        total_cap_variation = ((total_cap / total_cap_yesterday) - 1) * 100
        alt_cap_variation = ((alt_cap / alt_cap_yesterday) - 1) * 100
        with ui.card().props("flat bordered"):
            ui.label("Market Cap")
            with ui.row():
                with ui.column():
                    ui.label("Total").tailwind.font_weight("bold").text_color("orange-500")
                    ui.label(f"${self.human_format(total_cap)}").classes("text-xl")
                    if total_cap_variation > 0:
                        ui.label(f"↑ {round(total_cap_variation,2)}%").classes("text-positive")
                    else:
                        ui.label(f"↓ {round(total_cap_variation,2)}%").classes("text-negative")
                with ui.column():
                    ui.label("Altcoins").tailwind.font_weight("bold").text_color("gray-700")
                    ui.label(f"${self.human_format(alt_cap)}").classes("text-xl")
                    if alt_cap_variation > 0:
                        ui.label(f"↑ {round(alt_cap_variation,2)}%").classes("text-positive")
                    else:
                        ui.label(f"↓ {round(alt_cap_variation,2)}%").classes("text-negative")

    async def __render_prices(self):
        btc_variation = round(float(self.client.ticker_24hr(symbol="BTCUSDT")["priceChangePercent"]), 2)
        btc_price = round(float(self.client.avg_price(symbol="BTCUSDT")["price"]), 2)
        with ui.card().props("flat bordered"):
            with ui.column():
                ui.label("Prices")
                ui.label("BTC/USDT").tailwind.font_weight("bold").text_color("orange-500")
                ui.label(f"${btc_price}").classes("text-xl")
                if btc_variation > 0:
                    ui.label(f"↑ {round(btc_variation,2)}%").classes("text-positive")
                else:
                    ui.label(f"↓ {round(btc_variation,2)}%").classes("text-negative")

    async def __render_next_delist(self):
        try:
            data = self.client.delist_schedule_symbols()
            ui.label("Next delist")
            for delist in data:
                date = datetime.fromtimestamp(delist["delistTime"] / 1000)
                ui.label(f"{date.date()} -- {delist['symbols']}")
        except Exception as e:
            ui.label(f"Error fetching delist schedule: {str(e)}").classes("text-negative")

    async def render(self):
        coinmarketcap_data = await self.__get_market_data()
        with ui.card().props("flat bordered"):
            await self.__render_next_delist()

        with ui.row():
            await self.__render_bitcoin_dominance(coinmarketcap_data)
            await self.__render_prices()
            await self.__render_market_cap(coinmarketcap_data)

        with ui.card().props("flat bordered"):
            ui.label("Fear and Greed Index")
            await self.__render_fear_greed_index()
