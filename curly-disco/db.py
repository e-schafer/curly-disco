from pathlib import Path

from tortoise import Tortoise


class DB:
    @staticmethod
    async def init():
        db_dir = Path(__file__).parent.parent / "data"
        db_dir.mkdir(exist_ok=True)
        db_url = str("sqlite://" + str(db_dir) + "/db.sqlite3")
        await Tortoise.init(db_url=db_url, modules={"models": ["models"]})
        await Tortoise.generate_schemas()

    @staticmethod
    async def close():
        await Tortoise.close_connections()


if __name__ == "__main__":
    import asyncio

    asyncio.run(DB.init())
    asyncio.run(DB.close())
