import aiohttp


async def get_from_web_api(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            return await r.json()
