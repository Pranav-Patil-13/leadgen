import asyncio
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://www.google.com/maps/search/Software+Development+in+Pune"
        await page.goto(url)
        
        try:
            await page.wait_for_selector('div[role="feed"]', timeout=10000)
            await asyncio.sleep(2)
        except Exception as e:
            print("Feed not found")
            await browser.close()
            return
            
        print("Scrolling...")
        
        cards = await page.query_selector_all('div[role="article"]')
        print(f"Found {len(cards)} cards")
        
        for card in cards[:3]:
            name = await card.get_attribute('aria-label')
            text_content = await card.inner_text()
            lines = text_content.split('\n')
            
            # Find links
            links = await card.query_selector_all('a')
            hrefs = []
            for a in links:
                h = await a.get_attribute('href')
                if h: hrefs.append(h)
                
            print(f"Name: {name}")
            print(f"Hrefs: {hrefs}")
            print("-" * 20)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
