import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import re
import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.models import Lead, LeadPipeline, LeadActivity

async def extract_info_from_website(url: str) -> Dict[str, Any]:
    info = {"email": None, "social_links": None}
    
    # Try different URL formats
    urls_to_try = [url]
    if not url.startswith('http'):
        urls_to_try = [f"https://{url}", f"http://{url}"]
        
    for current_url in urls_to_try:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
                }
                async with session.get(current_url, headers=headers, timeout=10, ssl=False) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Regex for email
                        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)
                        valid_emails = [e for e in emails if not e.endswith(('.png', '.webp', '.jpg', '.jpeg', '.gif', '.css', '.js')) and 'wixpress' not in e]
                        if valid_emails:
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
                                        if key not in found_socials:
                                            found_socials[key] = href
                        
                        if found_socials:
                            info["social_links"] = json.dumps(found_socials)
                        
                        return info # Successfully got it
        except Exception:
            pass
            
    return info

async def search_google_maps(industry: str, location: str, min_rating: Any = 0, requires_website: bool = False) -> List[Dict[str, Any]]:
    """
    Scrapes business data from Google Maps based on criteria.
    """
    try:
        min_rating = float(min_rating)
    except (ValueError, TypeError):
        min_rating = 0.0

    search_query = f"{industry} in {location}"
    print(f"DEBUG: Searching Google Maps for: {search_query}")
    results = []

    async with async_playwright() as p:
        # Launch with some arguments to avoid being blocked easily
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Navigate to Google Maps search
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        await page.goto(url)
        
        # Wait for results or 'not found'
        try:
            # Wait for either results or a 'no results' message
            await page.wait_for_selector('div[role="feed"]', timeout=15000)
            await asyncio.sleep(2)
        except:
            print(f"DEBUG: No feed found for query: {search_query}")
            await browser.close()
            return []

        # Scroll the specific feed container
        scrollable_div = await page.query_selector('div[role="feed"]')
        if scrollable_div:
            print(f"DEBUG: Starting scroll for more leads...")
            for i in range(15):  # Increased from 5 to 15 scrolls
                await scrollable_div.hover()
                await page.mouse.wheel(0, 5000)  # Increased scroll distance
                await asyncio.sleep(1.5)
                # Check if we hit the end
                if i % 5 == 0:
                    # Occasional scroll up and down to trigger loading
                    await page.mouse.wheel(0, -500)
                    await asyncio.sleep(0.5)
                    await page.mouse.wheel(0, 1000)

        # Get all business cards
        # Google Maps uses different classes, but aria-label on cards is usually reliable
        cards = await page.query_selector_all('div[role="article"]')
        print(f"DEBUG: Found {len(cards)} raw cards on page")
        
        for card in cards:
            try:
                # Name is usually in a div with specific font classes or aria-label
                name = await card.get_attribute('aria-label')
                if not name:
                    continue

                # Negative Keyword Filter: Skip if business is a software/tech company
                # Rationale: User specifically wants to avoid targeting their own industry
                negative_keywords = ['software', 'it services', 'solutions', 'digital agency', 'web design', 'tech']
                if any(kw in name.lower() for kw in negative_keywords):
                    print(f"DEBUG: Skipping potential competitor: {name}")
                    continue

                # Rating parsing - more robust
                rating = 0.0
                rating_el = await card.query_selector('span[aria-label*="stars"]')
                if rating_el:
                    rating_text = await rating_el.get_attribute('aria-label')
                    if rating_text:
                        # Extract "4.5" from "4.5 stars"
                        match = re.search(r'([0-9.]+)', rating_text)
                        if match:
                            rating = float(match.group(1))
                
                if rating < min_rating:
                    continue

                # Website and Maps URL
                links = await card.query_selector_all('a')
                website = None
                maps_url = None
                
                for a in links:
                    h = await a.get_attribute('href')
                    if h:
                        if 'google.com/maps/place' in h:
                            maps_url = h
                        elif 'http' in h and 'google.com' not in h:
                            # Verify it's not a generic social link or share link
                            if not any(x in h for x in ['facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com']):
                                website = h
                
                if requires_website and not website:
                    continue

                # Find phone - look for specific phone icon/container or regex
                phone = None
                
                # Method 1: Look for tel links (most reliable)
                tel_link = await card.query_selector('a[href^="tel:"]')
                if tel_link:
                    phone_href = await tel_link.get_attribute('href')
                    if phone_href:
                        phone = phone_href.replace('tel:', '').strip()
                
                # Method 2: Search text content for phone patterns if Method 1 fails
                if not phone:
                    text_content = await card.inner_text()
                    # Improved regex to handle various international formats and avoid missing last digits
                    # Handles: +91 99216 01234, 020 2636 1234, 917-262-3879, etc.
                    phone_match = re.search(r'(\+?\d{1,4}[\s-]?)?\(?\d{2,5}\)?[\s-]?\d{3,5}[\s-]?\d{3,5}', text_content)
                    if phone_match:
                        phone = phone_match.group(0).strip()
                
                # Method 3: Check aria-label of all elements in card
                if not phone:
                    all_els = await card.query_selector_all('*[aria-label]')
                    for el in all_els:
                        label = await el.get_attribute('aria-label')
                        if label and 'Phone' in label:
                            # Extract digits from label
                            phone_digits = "".join(re.findall(r'[\d\+\s\-\(\)]+', label)).strip()
                            if len(re.sub(r'\D', '', phone_digits)) >= 7:
                                phone = phone_digits
                                break

                results.append({
                    "company_name": name,
                    "website": website,
                    "phone": phone,
                    "email": None,
                    "city": location,
                    "rating": str(rating),
                    "google_maps_url": maps_url,
                    "social_links": None,
                    "status": "New Lead"
                })
            except Exception as e:
                print(f"DEBUG: Error processing card: {e}")
                continue

        await browser.close()
        
        # Parallel Enrichment from Website (Email, Socials)
        print(f"DEBUG: Starting parallel enrichment for {len(results)} leads...")
        
        async def enrich_lead(lead):
            if lead["website"]:
                try:
                    # Use a shorter timeout for enrichment
                    info = await asyncio.wait_for(extract_info_from_website(lead["website"]), timeout=10)
                    lead["email"] = info.get("email")
                    lead["social_links"] = info.get("social_links")
                except Exception:
                    pass
            return lead

        # Process in chunks of 10 to avoid overwhelming the system
        chunk_size = 10
        for i in range(0, len(results), chunk_size):
            chunk = results[i:i + chunk_size]
            await asyncio.gather(*(enrich_lead(lead) for lead in chunk))
            print(f"DEBUG: Enriched {min(i + chunk_size, len(results))}/{len(results)} leads")
    
    return results

async def search_reddit(keywords: str) -> List[Dict[str, Any]]:
    """
    Search Reddit for potential leads based on intent keywords.
    """
    results = []
    print(f"DEBUG: Searching Reddit for: {keywords}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Search URL
        search_url = f"https://www.reddit.com/search/?q={keywords.replace(' ', '%20')}&t=week"
        await page.goto(search_url)
        
        try:
            # Wait for search results
            await page.wait_for_selector('div[data-testid="post-container"]', timeout=15000)
        except:
            print("DEBUG: No Reddit results found or timed out.")
            await browser.close()
            return []

        # Extract post details
        posts = await page.query_selector_all('div[data-testid="post-container"]')
        for post in posts:
            try:
                # Title
                title_el = await post.query_selector('h3')
                title = await title_el.inner_text() if title_el else "Reddit Post"
                
                # Snippet/Content
                snippet_el = await post.query_selector('div[data-click-id="text"]')
                snippet = await snippet_el.inner_text() if snippet_el else ""
                
                # Author
                author_el = await post.query_selector('a[data-testid="post_author_link"]')
                author = await author_el.inner_text() if author_el else "Unknown"
                
                # URL
                post_link_el = await post.query_selector('a[data-click-id="body"]')
                post_url = "https://www.reddit.com" + await post_link_el.get_attribute('href') if post_link_el else ""

                results.append({
                    "company_name": f"Reddit: {author}", # Repurposing company_name for author
                    "website": post_url,
                    "phone": None,
                    "email": None,
                    "city": "Reddit",
                    "rating": "0",
                    "google_maps_url": None,
                    "social_links": json.dumps({"reddit": post_url}),
                    "status": "New Lead",
                    "source": "Reddit",
                    "intent_data": f"Title: {title}\nSnippet: {snippet}"
                })
            except Exception as e:
                print(f"DEBUG: Error parsing Reddit post: {e}")
                continue
                
        await browser.close()
        
    return results

async def is_duplicate(session: AsyncSession, company_name: str, website: str = None) -> bool:
    """Checks if lead already exists by name or website."""
    query = select(Lead).where(Lead.company_name == company_name)
    if website:
        query = query.filter((Lead.company_name == company_name) | (Lead.website == website))
    
    result = await session.execute(query)
    return result.scalars().first() is not None

@celery_app.task(name="run_pipeline")
def run_pipeline_task(pipeline_id: int):
    """Celery task to run a specific pipeline."""
    return asyncio.run(process_pipeline(pipeline_id))

async def process_pipeline(pipeline_id: int):
    """Async logic to process a pipeline."""
    async with async_session_factory() as session:
        # Get pipeline
        pipeline = await session.get(LeadPipeline, pipeline_id)
        if not pipeline or not pipeline.is_active:
            return 0

        # Run scraper based on platform
        if pipeline.platform == "Reddit":
            discovered_leads = await search_reddit(pipeline.industry)
        else:
            discovered_leads = await search_google_maps(
                industry=pipeline.industry,
                location=pipeline.location,
                min_rating=pipeline.minimum_rating,
                requires_website=pipeline.requires_website
            )
        
        print(f"Scraper returned {len(discovered_leads)} raw leads for pipeline {pipeline_id}")

        from app.services.scoring import calculate_lead_score

        # Filter duplicates first
        new_leads_data = []
        for data in discovered_leads:
            if not await is_duplicate(session, data["company_name"], data.get("website")):
                new_leads_data.append(data)
        
        print(f"Processing {len(new_leads_data)} non-duplicate leads...")

        new_count = 0
        for data in new_leads_data:
            # Calculate AI Score
            score, label, tags = calculate_lead_score(data)
            
            lead = Lead(
                **data,
                pipeline_id=pipeline_id,
                ai_score=score,
                ai_score_label=label,
                opportunity_tags=json.dumps(tags),
                source=data.get("source", "Scraper"),
                intent_data=data.get("intent_data")
            )
            session.add(lead)
            new_count += 1
        
        if new_count > 0:
            pipeline.total_leads_found = (pipeline.total_leads_found or 0) + new_count
            pipeline.last_run = datetime.utcnow()
            await session.commit()
            print(f"Pipeline '{pipeline.name}' saved {new_count} new leads.")
        else:
            print("No new leads to save.")

        return new_count

@celery_app.task(name="run_all_pipelines")
def run_all_pipelines_task():
    """Runs all active pipelines sequentially."""
    asyncio.run(process_all_pipelines())

async def process_all_pipelines():
    async with async_session_factory() as session:
        result = await session.execute(select(LeadPipeline).where(LeadPipeline.is_active == True))
        pipelines = result.scalars().all()
        
        for p in pipelines:
            await process_pipeline(p.id)
