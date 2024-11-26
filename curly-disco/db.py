from tortoise import Tortoise


class DB:
    @staticmethod
    async def init():
        await Tortoise.init(
            db_url="sqlite://db.sqlite3", modules={"models": ["models"]}
        )
        await Tortoise.generate_schemas()

    @staticmethod
    async def close():
        await Tortoise.close_connections()


if __name__ == "__main__":
    import asyncio

    asyncio.run(DB.init())
    asyncio.run(DB.close())
