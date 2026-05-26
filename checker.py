import asyncio
import database as db
from scraper import scrape_flipkart
from telegram_bot import send_price_drop_alert, send_message


async def check_single_product(product: dict) -> None:
    """Scrape one product and trigger alert if price dropped below target."""
    print(f"[checker] Checking: {product['name']}")

    result = await scrape_flipkart(product["url"])
    if not result:
        print(f"[checker] Failed to scrape: {product['url']}")
        return

    current_price = result["price"]

    # Save to history
    db.save_price(product["id"], current_price)

    # Get previous price (second-latest entry)
    history = db.get_price_history(product["id"], limit=2)
    old_price = history[1]["price"] if len(history) >= 2 else current_price

    print(f"[checker] {product['name']}: Rs.{current_price:,} (target Rs.{product['target_price']:,})")

    # Alert if price dropped AND is at or below target
    if current_price <= product["target_price"]:
        print(f"[checker] TARGET REACHED — sending alert!")
        await send_price_drop_alert(product, old_price, current_price)

    # Also alert if there's any price drop (even above target)
    elif current_price < old_price:
        drop = old_price - current_price
        print(f"[checker] Price dropped by Rs.{drop:,} — sending update")
        await send_price_drop_alert(product, old_price, current_price)


async def check_all_products() -> None:
    """Check all active products — called by scheduler and GitHub Actions."""
    products = db.get_all_active_products()

    if not products:
        print("[checker] No products to check.")
        return

    print(f"[checker] Checking {len(products)} product(s)...")

    # Check one by one with a small delay to avoid rate limiting
    for product in products:
        await check_single_product(product)
        await asyncio.sleep(3)

    print("[checker] Done.")


# Allow running directly: python checker.py
if __name__ == "__main__":
    asyncio.run(check_all_products())