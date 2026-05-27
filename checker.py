async def check_all_products() -> None:
    """Check all active products — called by scheduler and GitHub Actions."""
    products = db.get_all_active_products()
    if not products:
        print("[checker] No products to check.")
        await send_message("🔍 Price check started — no products tracked yet.\nSend /add to add a product.")
        return

    # Opening heartbeat
    lines = [f"  • {p['name']} (target: Rs.{p['target_price']:,})" for p in products]
    await send_message(
        f"🔍 <b>Price check started</b>\n\n"
        f"Checking {len(products)} product(s):\n" + "\n".join(lines)
    )

    results = []
    for product in products:
        await check_single_product(product)
        # Grab latest price for summary
        history = db.get_price_history(product["id"], limit=1)
        if history:
            current = history[0]["price"]
            gap = current - product["target_price"]
            if gap <= 0:
                status = "🚨 Alert sent!"
            else:
                status = f"Rs.{gap:,} above target"
            results.append(f"  • {product['name']}\n    Rs.{current:,} — {status}")
        await asyncio.sleep(3)

    # Closing summary
    await send_message(
        f"✅ <b>Check complete</b>\n\n"
        + "\n\n".join(results)
        + "\n\n⏰ Next check in ~3 hours"
    )
    print("[checker] Done.")
