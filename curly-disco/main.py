from db import DB
from nicegui import app, ui
from pages import trades_view

# app.on_connect(DB.init())
# app.on_connect(DB.close())


@ui.page("/", title="Curly Disco")
async def index():
    with ui.header().classes(replace="row items-center") as header:
        ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props(
            "flat color=white"
        )
        with ui.tabs() as tabs:
            ui.tab("Trades")
            ui.tab("B")
            ui.tab("C")

    with ui.left_drawer().classes("bg-blue-100") as left_drawer:
        ui.label("Side menu")

    with ui.tab_panels():
        trades_view.trades_view()


ui.run()
