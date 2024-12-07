import os

import models
import watcher
from db import DB
from nicegui import app, ui

app.on_startup(DB.init())
app.on_disconnect(DB.close())
_watcher = watcher.Watcher(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])


NUMBER_OF_ITEMS = 20


def slot_link():
    return """
    <q-td :props="props">
        <a :href="https://fr.tradingview.com/chart/?symbol=BINANCE:props.value">{0}</a>
    </q-td>
    """.format("{{ props.value }}")


def slot_red_green(col_name: str, symbol: str = "%"):
    return """
    <q-td align="middle">
        <q-badge key="{0}" :props="props" outline  :color="props.value < 0 ? 'red':'green'">
            {1} {2}
        </q-badge>
    </q-td>
    """.format(col_name, "{{props.value.toFixed(2)}}", symbol)


def slot_timestamp(col_name: str):
    return """
    <q-td align="middle">
        <q-badge key="{0}" :props="props" outline>
            {1}
        </q-badge>
    </q-td>
    """.format(col_name, "{{typeof(props.value)}}")


def slot_far(col_name: str):
    return """
    <q-td align="middle">
        <q-badge key="{0}" :props="props" outline  :color="props.value < 0 ? 'red':'green'">
            {{props.value.toFixed(2)}} %
        </q-badge>
    </q-td>
    """.format(col_name)


@ui.refreshable
async def panel_asset():
    with ui.row():
        with ui.card().props("flat bordered"):
            ui.label("Total value")
            ui.label("1000$")
        with ui.card().props("flat bordered"):
            ui.label("Total gains")
            ui.label("1000$")
        with ui.card().props("flat bordered"):
            ui.label("Liquidity locked")
            ui.label("1000$")
        with ui.card().props("flat bordered"):
            ui.label("Liquidity available")
            ui.label("1000$")
    ui.label("Current assets")
    with ui.table(
        columns=models.Assets.nicegui_repr(),
        rows=await _watcher.get_upto_date_asset(),
        row_key="id",
        pagination=NUMBER_OF_ITEMS,
    ) as home_table:
        home_table.add_slot(
            "body-cell-id",
            """
            <q-td :props="props">
                <a :href="props.value">{{ props.value }}</a>
            </q-td>
            """,
        )
        home_table.add_slot("loading", "True")
        home_table.add_slot("body-cell-gains", slot_red_green("gains", "$"))
        home_table.add_slot("body-cell-gains_percentage", slot_red_green("gains_percentage", "%"))
        # home_table.add_slot("body-cell-updated_at", slot_timestamp("updated_at"))


@ui.refreshable
async def panel_open_orders():
    order_columns = [
        {"name": "Pair", "label": "pair", "field": "pair", "sortable": True},
        {"name": "Quantity", "label": "quantity", "field": "quantity", "sortable": True},
        {"name": "Current price", "label": "current", "field": "current_price", "sortable": True},
        {"name": "Target price", "label": "target", "field": "target_price", "sortable": True},
        {"name": "Far", "label": "far", "field": "far", "sortable": True},
    ]
    open_orders = await _watcher.get_opened_buy_orders()
    ui.table(columns=order_columns, rows=open_orders, pagination=NUMBER_OF_ITEMS, row_key="pair")


@ui.refreshable
async def panel_trades():
    trades = await models.Trades.all().values()
    trades.sort(key=lambda x: x["closed_at"], reverse=True)
    with ui.table(
        columns=models.Trades.nicegui_repr(), rows=trades, pagination=NUMBER_OF_ITEMS, row_key="id"
    ) as trades_table:
        trades_table.add_slot("body-cell-gains", slot_red_green("gains", "$"))
        trades_table.add_slot("body-cell-gains_percentage", slot_red_green("gains_percentage", "%"))


@ui.page("/", title="Curly Disco", response_timeout=20.0)
async def index():
    with ui.header().classes(replace="row items-center"):
        # ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props("flat color=white")
        with ui.tabs() as tabs:
            ui.tab("Home")
            ui.tab("Open orders")
            ui.tab("Trades")
            ui.tab("Controls")

    # with ui.left_drawer().classes("bg-blue-100") as left_drawer:
    #     ui.label("Side menu")

    with ui.tab_panels(tabs, value="Home"):
        with ui.tab_panel("Home"):
            ui.button("Refresh", on_click=panel_asset.refresh)
            await panel_asset()
        with ui.tab_panel("Open orders"):
            ui.button("Refresh", on_click=panel_open_orders.refresh)
            await panel_open_orders()

        with ui.tab_panel("Trades").classes("w-full"):
            ui.button("Refresh", on_click=panel_trades.refresh)
            await panel_trades()
        with ui.tab_panel("Controls"):
            ui.label("Controls")


ui.dark_mode(value=True)
ui.run()
