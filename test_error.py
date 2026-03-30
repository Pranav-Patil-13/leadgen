import asyncio
from httpx import AsyncClient
from app.main import app

async def main():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/login")
        print(response.status_code, response.text)

asyncio.run(main())
