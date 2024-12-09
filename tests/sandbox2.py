import asyncio

from nicegui import ui


async def count():
    print("count")
    await asyncio.sleep(20)
    print("done")


async def start():
    print("click start")
    ui.notify("Starting...")
    await count()
    ui.notify("Done!")


@ui.page("/")
async def main():
    ui.button("Start", on_click=lambda: start())


ui.run(reload=False)
