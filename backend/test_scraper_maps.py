import asyncio
from app.services.scraper_tasks import search_google_maps

async def run_test():
    print("Running scraper test...")
    results = await search_google_maps(industry="Software Development", location="Pune", min_rating=0, requires_website=False)
    print(f"Scraper returned {len(results)} results")
    for r in results[:3]:
        print(f"Name: {r.get('company_name')}")
        print(f"Website: {r.get('website')}")
        print(f"Phone: {r.get('phone')}")
        print(f"Email: {r.get('email')}")
        print(f"Social Links: {r.get('social_links')}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(run_test())
