import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/login")
        print(response.status_code, response.text)

        response = await ac.get("/")
        print(response.status_code, response.text)

asyncio.run(main())
