import asyncio
from scraper import scrape_flipkart
from database import add_product, save_price, get_all_active_products
from telegram_bot import send_price_drop_alert, send_message

async def test():
    print("Step 1: Scraping Flipkart...")
    url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4"
    result = await scrape_flipkart(url)
    print(f"Got: {result['name']} at Rs.{result['price']:,}")

    print("\nStep 2: Saving to Supabase...")
    product = add_product(url, result['name'], 70000)
    save_price(product['id'], result['price'])
    print(f"Saved! Product ID: {product['id']}")

    print("\nStep 3: Sending Telegram alert...")
    await send_message(
        f"Full test complete!\n\n"
        f"Product: {result['name']}\n"
        f"Price: Rs.{result['price']:,}\n"
        f"Saved to Supabase successfully!"
    )
    print("Telegram message sent!")

    print("\nAll 3 steps working!")

asyncio.run(test())