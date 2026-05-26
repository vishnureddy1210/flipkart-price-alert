import re
import random
import asyncio
from playwright.async_api import async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

def clean_price(price_text: str) -> int | None:
    """Convert '₹1,23,456' to 123456"""
    try:
        digits = re.sub(r"[^\d]", "", price_text)
        return int(digits) if digits else None
    except Exception:
        return None

async def scrape_flipkart(url: str) -> dict | None:
    """
    Visit a Flipkart product URL and extract name + price safely.
    Returns: { "name": str, "price": int, "url": str } or None if it fails.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1366, "height": 768},
            locale="en-IN"
        )
        
        # Add basic client context variables to blend in with standard user traffic
        await context.set_extra_http_headers({
            "Accept-Language": "en-IN,en;q=0.9",
            "Connection": "keep-alive"
        })
        
        page = await context.new_page()
        
        # Native Stealth: Strip away automated navigator properties directly on page initialization
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            # Navigate immediately. Do not sleep on a blank page to avoid connection closure.
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait safely for dynamic layout assets to complete network transfers
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass # Networkidle timeouts happen easily; ignore and continue to parsing

            # Human-imitation reading delay after page elements are ready
            await asyncio.sleep(random.uniform(1.5, 2.5))

            # --- Extract product name ---
            name = None
            name_selectors = [
                "span.VU-ZEz",          # Current primary title class
                "span.B_NuCI",          # Alternate/Legacy title class
                "h1 span",             
                "h1.yhB1nd",           
                "h1",                  
            ]
            for sel in name_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        name = (await el.inner_text()).strip()
                        if name:
                            break
                except Exception:
                    continue

            # --- Extract price ---
            price = None
            price_selectors = [
                "div.Nx9bqj._4bCw3M",   # Specialized badge pricing
                "div.Nx9bqj",           # Standard global price class
                "div._30jeq3",          # Legacy target layout
                "div._16Jk6d",          
            ]
            
            for sel in price_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        raw = (await el.inner_text()).strip()
                        price = clean_price(raw)
                        if price:
                            break
                except Exception:
                    continue
            
            # --- Emergency Fallback: Dynamic body parsing loop ---
            if not price:
                try:
                    elements = await page.query_selector_all("div")
                    for element in elements:
                        text = await element.inner_text()
                        if "₹" in text and len(text.strip()) < 15 and any(c.isdigit() for c in text):
                            price = clean_price(text)
                            if price:
                                break
                except Exception:
                    pass

            if not price:
                print(f"[scraper] Could not find price on: {url}")
                return None

            return {
                "name": name or "Unknown Product",
                "price": price,
                "url": url,
            }

        except Exception as e:
            print(f"[scraper] Error scraping {url}: {e}")
            return None

        finally:
            await browser.close()

async def main():
    test_url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4"
    print(f"Starting test scrape for: {test_url}\n")
    
    result = await scrape_flipkart(test_url)
    
    print("\n--- Scraper Result ---")
    if result:
        print(f"Product: {result['name']}")
        print(f"Price  : ₹{result['price']:,}")
        print(f"URL    : {result['url']}")
    else:
        print("Failed to scrape data.")

if __name__ == "__main__":
    asyncio.run(main())