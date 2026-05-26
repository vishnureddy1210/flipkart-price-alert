import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


# ---------- Products ----------

def add_product(url: str, name: str, target_price: int) -> dict:
    """Add a new product to track."""
    db = get_client()
    result = db.table("products").insert({
        "url": url,
        "name": name,
        "target_price": target_price,
        "active": True,
    }).execute()
    return result.data[0]


def get_all_active_products() -> list[dict]:
    """Return all products that are actively being tracked."""
    db = get_client()
    result = db.table("products").select("*").eq("active", True).execute()
    return result.data


def delete_product(product_id: int) -> None:
    db = get_client()
    db.table("products").update({"active": False}).eq("id", product_id).execute()


# ---------- Price history ----------

def save_price(product_id: int, price: int) -> dict:
    """Save a price check result."""
    db = get_client()
    result = db.table("price_history").insert({
        "product_id": product_id,
        "price": price,
    }).execute()
    return result.data[0]


def get_price_history(product_id: int, limit: int = 30) -> list[dict]:
    """Get the last N price records for a product."""
    db = get_client()
    result = (
        db.table("price_history")
        .select("*")
        .eq("product_id", product_id)
        .order("checked_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def get_lowest_price(product_id: int) -> int | None:
    """Return the all-time lowest recorded price for a product."""
    history = get_price_history(product_id, limit=100)
    if not history:
        return None
    return min(h["price"] for h in history)