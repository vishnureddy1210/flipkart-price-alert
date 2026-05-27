import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_URL  = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(text: str) -> bool:
    """Send a plain-text Telegram message."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[telegram] BOT_TOKEN or CHAT_ID not set — skipping send")
        return False
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        })
        return resp.status_code == 200


async def resolve_flipkart_url(deep_url: str) -> str | None:
    """
    Convert a dl.flipkart.com deep link to a proper www.flipkart.com product URL.
    Uses Playwright to follow the redirect inside a real browser.
    Returns the resolved URL or None if it fails.
    """
    from playwright.async_api import async_playwright
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            await page.goto(deep_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
            final_url = page.url
            await browser.close()

            # Must land on a proper product page
            if "flipkart.com" in final_url and "/p/" in final_url:
                print(f"[resolver] Resolved: {final_url}")
                return final_url
            else:
                print(f"[resolver] Could not resolve to product page. Got: {final_url}")
                return None
    except Exception as e:
        print(f"[resolver] Error: {e}")
        return None


async def send_price_drop_alert(product: dict, old_price: int, new_price: int) -> None:
    """Send a formatted price-drop alert."""
    saving = old_price - new_price
    pct    = round((saving / old_price) * 100)
    msg = (
        f"🔥 <b>Price Drop Alert!</b>\n\n"
        f"<b>{product['name']}</b>\n\n"
        f"Was:    <s>Rs.{old_price:,}</s>\n"
        f"Now:    <b>Rs.{new_price:,}</b>\n"
        f"Target: Rs.{product['target_price']:,}\n\n"
        f"You save Rs.{saving:,} ({pct}% off)\n\n"
        f"<a href=\"{product['url']}\">Buy on Flipkart</a>"
    )
    await send_message(msg)


async def send_check_result(product: dict, current_price: int) -> None:
    """Reply to a /check command with the current price."""
    gap = current_price - product["target_price"]
    status = "🎯 Target reached!" if gap <= 0 else f"Rs.{gap:,} above your target"
    msg = (
        f"<b>{product['name']}</b>\n\n"
        f"Current price: <b>Rs.{current_price:,}</b>\n"
        f"Your target:   Rs.{product['target_price']:,}\n"
        f"Status: {status}\n\n"
        f"<a href=\"{product['url']}\">View on Flipkart</a>"
    )
    await send_message(msg)


# ---- Telegram bot command handler (polling) ----

async def handle_updates() -> None:
    """
    Long-poll Telegram for /check, /list, /add, /remove, /help commands.
    Run this as a background task.
    """
    import database as db
    from scraper import scrape_flipkart

    offset = 0
    print("[bot] Listening for Telegram commands...")

    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                resp = await client.get(f"{BASE_URL}/getUpdates", params={
                    "offset": offset,
                    "timeout": 30,
                })
                updates = resp.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "").strip()

                # ---- /list ----
                if text == "/list":
                    products = db.get_all_active_products()
                    if not products:
                        await send_message(
                            "No products being tracked yet.\n\n"
                            "Use /add to add one:\n"
                            "<code>/add &lt;flipkart_url&gt; &lt;target_price&gt;</code>"
                        )
                    else:
                        lines = [
                            f"{i+1}. {p['name']}\n"
                            f"    Target: Rs.{p['target_price']:,}\n"
                            f"    /remove_{p['id']}"
                            for i, p in enumerate(products)
                        ]
                        await send_message("📋 <b>Tracked products:</b>\n\n" + "\n\n".join(lines))

                # ---- /add ----
                elif text.startswith("/add"):
                    parts = text.split()

                    if len(parts) != 3:
                        await send_message(
                            "⚠️ <b>Wrong format.</b> Use:\n\n"
                            "<code>/add &lt;flipkart_url&gt; &lt;target_price&gt;</code>\n\n"
                            "Example:\n"
                            "<code>/add https://www.flipkart.com/iphone-15/p/abc123 55000</code>\n\n"
                            "You can also paste deep links from the Flipkart app directly!"
                        )
                        continue

                    url = parts[1]

                    if not parts[2].isdigit():
                        await send_message(
                            "⚠️ Target price must be a number.\n\n"
                            "Example: <code>/add &lt;url&gt; 55000</code>"
                        )
                        continue

                    target_price = int(parts[2])

                    if "flipkart.com" not in url:
                        await send_message(
                            "⚠️ Only Flipkart URLs are supported.\n"
                            "Make sure your URL contains <code>flipkart.com</code>"
                        )
                        continue

                    # ---- Auto-resolve deep links ----
                    if "dl.flipkart.com" in url:
                        await send_message("🔄 Deep link detected — resolving to product page, please wait...")
                        resolved = await resolve_flipkart_url(url)
                        if not resolved:
                            await send_message(
                                "❌ Could not resolve this deep link automatically.\n\n"
                                "Please:\n"
                                "1. Open the link in your browser\n"
                                "2. Copy the URL from the address bar\n"
                                "3. Use that URL with /add instead"
                            )
                            continue
                        url = resolved
                        await send_message(f"✅ Resolved to:\n<code>{url}</code>")

                    # ---- Save to database ----
                    try:
                        product = db.add_product(
                            url=url,
                            name="⏳ Fetching item details on next background sync...",
                            target_price=target_price,
                        )
                        db.save_price(product["id"], 0)

                        await send_message(
                            f"✅ <b>Link added successfully!</b>\n\n"
                            f"Target Price: <b>Rs.{target_price:,}</b>\n\n"
                            f"⚙️ GitHub Actions will identify the product and update its price shortly!"
                        )
                    except Exception as db_err:
                        print(f"[bot] Database write failure: {db_err}")
                        await send_message("❌ Failed to save. Please try again.")

                # ---- /remove_<id> ----
                elif text.startswith("/remove_"):
                    try:
                        product_id = int(text.split("_")[1])
                        products = db.get_all_active_products()
                        product = next((p for p in products if p["id"] == product_id), None)
                        if not product:
                            await send_message("⚠️ Product not found. Use /list to see tracked products.")
                        else:
                            db.delete_product(product_id)
                            await send_message(f"🗑️ Removed <b>{product['name']}</b> from tracking.")
                    except (IndexError, ValueError):
                        await send_message("⚠️ Invalid remove command. Use /list to see products with remove links.")

                # ---- /check ----
                elif text.startswith("/check"):
                    products = db.get_all_active_products()
                    if not products:
                        await send_message("No products being tracked.\n\nUse /add to add one.")
                    else:
                        await send_message(f"🔍 Checking {len(products)} product(s)... please wait.")
                        for product in products:
                            result = await scrape_flipkart(product["url"])
                            if result:
                                await send_check_result(product, result["price"])
                            else:
                                await send_message(f"❌ Could not fetch price for {product['name']}")

                # ---- /help ----
                elif text.startswith("/help"):
                    await send_message(
                        "<b>📱 Flipkart Alert Bot — Commands</b>\n\n"
                        "/add &lt;url&gt; &lt;price&gt; — track a product\n"
                        "Works with both www and app (dl.) links!\n"
                        "Example: <code>/add https://flipkart.com/... 55000</code>\n\n"
                        "/list — show all tracked products\n"
                        "/check — check all prices right now\n"
                        "/help — show this message\n\n"
                        "To remove a product, use /list and tap the remove link."
                    )

        except Exception as e:
            print(f"[bot] Polling error: {e}")
            await asyncio.sleep(5)
