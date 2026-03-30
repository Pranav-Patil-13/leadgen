import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json

async def extract_info_from_website(url: str):
    info = {"email": None, "social_links": {}}
    
    # Try different URL formats
    urls_to_try = [url]
    if not url.startswith('http'):
        urls_to_try = [f"https://{url}", f"http://{url}"]
        
    for current_url in urls_to_try:
        try:
            async with aiohttp.ClientSession() as session:
                # Use a standard user agent to avoid being blocked
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
                }
                async with session.get(current_url, headers=headers, timeout=10, ssl=False) as response:
                    print(f"Trying {current_url} - Status: {response.status}")
                    if response.status == 200:
                        html = await response.text()
                        
                        # Regex for email
                        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)
                        valid_emails = [e for e in emails if not e.endswith(('.png', '.webp', '.jpg', '.jpeg', '.gif', '.css', '.js')) and 'wixpress' not in e]
                        if valid_emails:
                            # Return the most likely primary email if multiple exist
                            info["email"] = valid_emails[0]
                        
                        # BeautifulSoup for social links
                        soup = BeautifulSoup(html, "html.parser")
                        links = soup.find_all('a', href=True)
                        
                        social_platforms = ['linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com']
                        found_socials = {}
                        for link in links:
                            href = link['href']
                            for platform in social_platforms:
                                if platform in href and platform not in found_socials:
                                    # basic filter to avoid share links if possible
                                    if 'share' not in href.lower() and 'intent' not in href.lower() and 'tweet' not in href.lower():
                                        key = platform.split('.')[0]
                                        # only add if not already added to prevent overwriting with junk
                                        if key not in found_socials:
                                            found_socials[key] = href
                        
                        if found_socials:
                            info["social_links"] = json.dumps(found_socials)
                        
                        return info # Successfully got it
        except Exception as e:
            print(f"Error accessing {current_url}: {e}")
            pass
            
    return info

async def run_test():
    urls = [
        "https://www.google.com",
        "https://www.joshsoftware.com/",
        "https://www.apple.com"
    ]
    for url in urls:
        print(f"Testing {url}:")
        info = await extract_info_from_website(url)
        print(info)
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(run_test())
