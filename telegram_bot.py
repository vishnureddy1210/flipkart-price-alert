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


async def send_price_drop_alert(product: dict, old_price: int, new_price: int) -> None:
    """Send a formatted price-drop alert."""
    saving = old_price - new_price
    pct    = round((saving / old_price) * 100)
    msg = (
        f"<b>Price Drop Alert!</b>\n\n"
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
    status = "Target reached!" if gap <= 0 else f"Rs.{gap:,} above your target"
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
    Long-poll Telegram for /check, /list, /add commands.
    Run this as a background task.
    """
    import database as db

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

                if text == "/list":
                    products = db.get_all_active_products()
                    if not products:
                        await send_message("No products being tracked yet.\nUse /add to add one.")
                    else:
                        lines = [f"{i+1}. {p['name']} — Rs.{p['target_price']:,}" for i, p in enumerate(products)]
                        await send_message("Tracked products:\n\n" + "\n".join(lines))

                elif text.startswith("/check"):
                    products = db.get_all_active_products()
                    if not products:
                        await send_message("No products being tracked.")
                    else:
                        await send_message(f"Checking {len(products)} product(s)... please wait.")
                        from scraper import scrape_flipkart
                        for product in products:
                            result = await scrape_flipkart(product["url"])
                            if result:
                                await send_check_result(product, result["price"])
                            else:
                                await send_message(f"Could not fetch price for {product['name']}")

                elif text.startswith("/help"):
                    await send_message(
                        "<b>Available commands:</b>\n\n"
                        "/list — show all tracked products\n"
                        "/check — check prices right now\n"
                        "/help — show this message"
                    )

        except Exception as e:
            print(f"[bot] Polling error: {e}")
            await asyncio.sleep(5)