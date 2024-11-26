from nicegui import ui


def trades_view():
    with ui.card() as card:
        ui.label("Trades view")
        ui.label("Coming soon...")
        ui.label("This page will display your trades history.")
        ui.label("For now, you can")
    return card
