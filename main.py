import asyncio
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db
from scraper import scrape_flipkart
from checker import check_all_products
from telegram_bot import handle_updates, send_message


# ---- Keep Render awake every 14 mins ----
async def keep_alive():
    url = os.environ.get("RENDER_URL", "")
    if not url:
        print("[keep-alive] RENDER_URL not set — skipping")
        return
    while True:
        await asyncio.sleep(14 * 60)
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{url}/", timeout=10)
                print("[keep-alive] pinged self successfully")
        except Exception as e:
            print(f"[keep-alive] error: {e}")


# ---- Lifespan: start Telegram polling + keep-alive on boot ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    task1 = asyncio.create_task(handle_updates())
    task2 = asyncio.create_task(keep_alive())
    yield
    task1.cancel()
    task2.cancel()


app = FastAPI(title="Flipkart Price Alert API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Request schemas ----
class AddProductRequest(BaseModel):
    url: str
    target_price: int


# ---- Routes ----
@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"status": "ok", "message": "Flipkart Price Alert API"}


@app.get("/api/products")
def list_products():
    """List all tracked products."""
    return db.get_all_active_products()


@app.post("/api/products")
async def add_product(req: AddProductRequest):
    """
    Add a new product to track.
    Scrapes Flipkart to confirm URL is valid and get product name.
    """
    result = await scrape_flipkart(req.url)
    if not result:
        raise HTTPException(status_code=400, detail="Could not fetch product from Flipkart. Check the URL.")

    product = db.add_product(
        url=req.url,
        name=result["name"],
        target_price=req.target_price,
    )
    db.save_price(product["id"], result["price"])

    await send_message(
        f"➕ <b>New product added!</b>\n\n"
        f"<b>{result['name']}</b>\n"
        f"Current price: Rs.{result['price']:,}\n"
        f"Your target:   Rs.{req.target_price:,}\n\n"
        f"<a href=\"{req.url}\">View on Flipkart</a>"
    )
    return {
        "product": product,
        "current_price": result["price"],
        "message": f"Now tracking {result['name']} at Rs.{result['price']:,}",
    }


@app.delete("/api/products/{product_id}")
def remove_product(product_id: int):
    """Stop tracking a product."""
    db.delete_product(product_id)
    return {"message": "Product removed"}


@app.get("/api/products/{product_id}/history")
def price_history(product_id: int):
    """Get price history for a product."""
    return db.get_price_history(product_id)


@app.post("/api/check")
async def trigger_check():
    """Manually trigger a price check for all products."""
    await check_all_products()
    return {"message": "Check complete"}


@app.get("/api/products/{product_id}/check")
async def check_one(product_id: int):
    """Check price for a single product right now."""
    products = db.get_all_active_products()
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    result = await scrape_flipkart(product["url"])
    if not result:
        raise HTTPException(status_code=502, detail="Could not scrape Flipkart")

    db.save_price(product_id, result["price"])

    gap = result["price"] - product["target_price"]
    status = "🎯 Target reached!" if gap <= 0 else f"Rs.{gap:,} above your target"
    await send_message(
        f"🔍 <b>Single product check</b>\n\n"
        f"<b>{result['name']}</b>\n"
        f"Current price: Rs.{result['price']:,}\n"
        f"Your target:   Rs.{product['target_price']:,}\n"
        f"Status: {status}\n\n"
        f"<a href=\"{product['url']}\">View on Flipkart</a>"
    )
    return {
        "name": result["name"],
        "current_price": result["price"],
        "target_price": product["target_price"],
        "below_target": result["price"] <= product["target_price"],
    }
