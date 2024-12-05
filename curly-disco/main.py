import os

import models
import watcher
from db import DB
from nicegui import app, ui

app.on_startup(DB.init())
app.on_disconnect(DB.close())
_watcher = watcher.Watcher(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])


NUMBER_OF_ITEMS = 20


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
            ui.label("Home")
            with ui.table(
                columns=models.Assets.nicegui_repr(),
                rows=await _watcher.get_upto_date_asset(),
                row_key="id",
                pagination=NUMBER_OF_ITEMS,
            ) as home_table:
                home_table.add_slot("body-cell-gains", slot_red_green("gains", "$"))
                home_table.add_slot("body-cell-gains_percentage", slot_red_green("gains_percentage", "%"))
                home_table.add_slot("body-cell-updated_at", slot_timestamp("updated_at"))

        with ui.tab_panel("Open orders"):
            order_columns = [
                {"name": "Pair", "label": "pair", "field": "pair", "sortable": True},
                {"name": "Quantity", "label": "quantity", "field": "quantity", "sortable": True},
                {"name": "Current price", "label": "current", "field": "current_price", "sortable": True},
                {"name": "Target price", "label": "target", "field": "target_price", "sortable": True},
                {"name": "Far", "label": "far", "field": "far", "sortable": True},
            ]
            open_orders = await _watcher.buy_orders()
            ui.table(columns=order_columns, rows=open_orders, pagination=NUMBER_OF_ITEMS, row_key="pair")

        with ui.tab_panel("Trades").classes("w-full"):
            ui.label("Trades")
            trades = await models.Trades.all().values()
            trades.sort(key=lambda x: x["closed_at"], reverse=True)
            with ui.table(
                columns=models.Trades.nicegui_repr(), rows=trades, pagination=NUMBER_OF_ITEMS, row_key="id"
            ) as trades_table:
                trades_table.add_slot("body-cell-gains", slot_red_green("gains", "$"))
                trades_table.add_slot("body-cell-gains_percentage", slot_red_green("gains_percentage", "%"))

        with ui.tab_panel("Controls"):
            ui.label("Controls")


ui.dark_mode(value=True)
ui.run()
