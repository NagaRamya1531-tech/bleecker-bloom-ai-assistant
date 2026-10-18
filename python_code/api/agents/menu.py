"""The counter menu, read from products/products.jsonl (the single source of truth).

Usage, from python_code/api, to refresh products/menu_items_text.txt after editing the menu:
    python -m agents.menu
"""
import json
from pathlib import Path

PRODUCTS_DIR = Path(__file__).resolve().parents[2] / "products"
PRODUCTS_FILE = PRODUCTS_DIR / "products.jsonl"
MENU_TEXT_FILE = PRODUCTS_DIR / "menu_items_text.txt"


def load_products():
    with PRODUCTS_FILE.open(encoding="utf-8") as products_file:
        return [json.loads(line) for line in products_file if line.strip()]


def menu_prices():
    return {product["name"]: product["price"] for product in load_products()}


def match_menu_item(text, prices=None):
    """Map free text like "a cold brew" or "Dark Hot Chocolate (large)" to an exact menu name, or None."""
    prices = prices or menu_prices()
    text = str(text or "").strip().lower()
    exact = {name.lower(): name for name in prices}
    if text in exact:
        return exact[text]
    # Longest names first so "Iced Latte" is not matched as "Latte".
    return next((name for name in sorted(prices, key=len, reverse=True) if name.lower() in text), None)


def price_order(order_items, max_quantity=20):
    """Recompute an order from the menu: exact names, menu prices, merged duplicates.

    Items not on the menu are dropped, so neither the LLM nor the app can set a price.
    "price" is the line total (unit price x quantity), as the Order Taking Agent's prompt defines it.
    """
    prices = menu_prices()
    quantities = {}
    for item in order_items or []:
        name = match_menu_item(item.get("item") or item.get("name"), prices) if isinstance(item, dict) else None
        if not name:
            continue
        raw = item.get("quantity", item.get("quanitity"))
        try:
            quantity = 1 if raw in (None, "") else int(float(raw))  # an explicit 0 stays 0
        except (TypeError, ValueError):
            quantity = 1
        quantities[name] = min(max(quantities.get(name, 0) + quantity, 0), max_quantity)
    return [{"item": name, "quantity": quantity, "price": round(prices[name] * quantity, 2)}
            for name, quantity in quantities.items() if quantity > 0]


def menu_text():
    """The menu grouped by category, as plain text for prompts."""
    sections = {}
    for product in load_products():
        sections.setdefault(product["category"], []).append(f"{product['name']} - ${product['price']:.2f}")
    return "Menu Items\n\n" + "\n\n".join(
        f"{category}\n" + "\n".join(lines) for category, lines in sections.items()
    ) + "\n"


if __name__ == "__main__":
    MENU_TEXT_FILE.write_text(menu_text(), encoding="utf-8")
    print(f"Wrote {MENU_TEXT_FILE}")
