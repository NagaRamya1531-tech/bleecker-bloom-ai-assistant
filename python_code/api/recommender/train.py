"""Train the recommender from the April 2019 sales receipts.

Builds recommendation_objects/recommender.json with:
  - the app menu (price, category, ingredients, dietary tags from the knowledge base)
  - basket co-occurrence stats between menu items (support, confidence, lift)
  - popularity overall and per daypart (morning / midday / afternoon)
  - content-based proxies for menu items with no sales history (cold start)

Baskets are keyed by (transaction_id, transaction_date, sales_outlet_id).
transaction_id restarts every day, and about half the rows belong to the
anonymous customer 0, so keying by transaction_id + customer_id (as the
original notebook did) merges unrelated purchases into one basket.

Usage, from python_code/api:
    python -m recommender.train
"""
from collections import Counter, defaultdict
from itertools import combinations
import json
from pathlib import Path
import re

import pandas as pd

API_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = API_DIR.parent
DATASET_DIR = ROOT_DIR / "dataset"
PRODUCTS_FILE = ROOT_DIR / "products" / "products.jsonl"
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base"
OUTPUT_FILE = API_DIR / "recommendation_objects" / "recommender.json"

BASKET_KEY = ["transaction_id", "transaction_date", "sales_outlet_id"]
CAFFEINE_TAGS = {"contains-caffeine", "low-caffeine", "caffeine-free"}
DAYPARTS = {"morning": (0, 11), "midday": (11, 15), "afternoon": (15, 24)}


def daypart(hour):
    return next(name for name, (start, end) in DAYPARTS.items() if start <= hour < end)


def load_menu():
    """Menu items from products.jsonl, with dietary tags from the knowledge base."""
    menu = {}
    with PRODUCTS_FILE.open(encoding="utf-8") as products_file:
        for line in products_file:
            product = json.loads(line)
            menu[product["name"]] = {
                # Where the item appears in the sales data; items without these are new (cold start).
                "dataset_name": product.get("dataset_name"),
                "dataset_category": product.get("dataset_category"),
                "category": product["category"],
                "price": product["price"],
                "description": product["description"].split(". ")[0].rstrip(".") + ".",
                "ingredients": product["ingredients"],
                # Hand-picked item with sales history that a new item borrows pairings from.
                "similar_to": product.get("similar_to"),
                "tags": [],
            }

    for path in (KNOWLEDGE_BASE_DIR / "menu").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for section in re.split(r"^#{2,3}\s+", text, flags=re.MULTILINE)[1:]:
            name, _, body = section.partition("\n")
            tags = re.search(r"^Tags:\s*(.+)$", body, re.MULTILINE)
            if name.strip() in menu and tags:
                menu[name.strip()]["tags"] = [tag.strip() for tag in tags.group(1).split(",")]

    missing = [name for name, item in menu.items() if not item["tags"]]
    if missing:
        raise SystemExit(f"Menu items without 'Tags:' in the knowledge base: {missing}")
    # The caffeine filters rely on every item declaring exactly one caffeine level.
    bad_caffeine = [name for name, item in menu.items() if len(CAFFEINE_TAGS & set(item["tags"])) != 1]
    if bad_caffeine:
        raise SystemExit(f"Menu items need exactly one of {sorted(CAFFEINE_TAGS)} in 'Tags:': {bad_caffeine}")
    return menu


def load_sales(menu):
    """Sales line items mapped to menu item names (retail and off-menu items dropped)."""
    receipts = pd.read_csv(DATASET_DIR / "201904 sales reciepts.csv")
    products = pd.read_csv(DATASET_DIR / "product.csv")
    sales = receipts.merge(products[["product_id", "product", "product_category"]], on="product_id")

    # Sizes are separate products in the dataset ("Latte Rg", "Latte Lg").
    sales["dataset_name"] = sales["product"].str.replace(r" (Rg|Sm|Lg)$", "", regex=True).str.strip()
    # Match on category too: "Ethiopia" is both brewed coffee and a bag of beans, and
    # "Dark chocolate" is both a drink and a packaged retail item.
    menu_names = {(item["dataset_name"], item["dataset_category"]): name
                  for name, item in menu.items() if item["dataset_name"]}
    sales["item"] = [menu_names.get(key) for key in zip(sales["dataset_name"], sales["product_category"])]
    sales = sales[sales["item"].notna()].copy()
    sales["daypart"] = sales["transaction_time"].str[:2].astype(int).map(daypart)
    return sales


def basket_stats(sales):
    baskets = sales.groupby(BASKET_KEY).agg(items=("item", lambda items: sorted(set(items))),
                                            daypart=("daypart", "first"))
    item_counts, pair_counts = Counter(), Counter()
    daypart_counts = defaultdict(Counter)
    for items, part in zip(baskets["items"], baskets["daypart"]):
        item_counts.update(items)
        daypart_counts[part].update(items)
        for first, second in combinations(items, 2):
            pair_counts[(first, second)] += 1
            pair_counts[(second, first)] += 1
    return len(baskets), item_counts, pair_counts, daypart_counts


def co_occurrence(n_baskets, item_counts, pair_counts, min_pair_count=5):
    """For each item, the items bought with it, with confidence and lift."""
    rules = defaultdict(list)
    for (antecedent, consequent), count in pair_counts.items():
        if count < min_pair_count:
            continue
        confidence = count / item_counts[antecedent]
        lift = confidence / (item_counts[consequent] / n_baskets)
        rules[antecedent].append({
            "item": consequent,
            "pair_count": count,
            "confidence": round(confidence, 4),
            "lift": round(lift, 4),
        })
    for antecedent in rules:
        rules[antecedent].sort(key=lambda rule: rule["lift"], reverse=True)
    return dict(rules)


def content_proxies(menu, items_with_sales):
    """Map each menu item with no sales to a similar item that has sales.

    Uses the hand-picked "similar_to" from products.jsonl when present (e.g. Cold Brew ->
    Brazilian Organic Drip, made from the same beans). Otherwise falls back to the Jaccard
    overlap of ingredients, category, and dietary tags, which is unreliable when a new
    category has no items with sales, so new items should set "similar_to".
    """
    def features(name):
        item = menu[name]
        return {f"ingredient:{i.lower()}" for i in item["ingredients"]} | {f"category:{item['category']}"} | \
               {f"tag:{t}" for t in item["tags"]}

    proxies = {}
    for name in menu:
        if name in items_with_sales:
            continue
        if menu[name]["similar_to"] in items_with_sales:
            a, b = features(name), features(menu[name]["similar_to"])
            proxies[name] = {"proxy": menu[name]["similar_to"], "similarity": round(len(a & b) / len(a | b), 3),
                             "source": "curated"}
            continue
        scored = []
        for candidate in items_with_sales:
            a, b = features(name), features(candidate)
            scored.append((len(a & b) / len(a | b), candidate))
        similarity, proxy = max(scored)
        proxies[name] = {"proxy": proxy, "similarity": round(similarity, 3), "source": "content"}
    return proxies


def train(sales, menu):
    n_baskets, item_counts, pair_counts, daypart_counts = basket_stats(sales)
    return {
        "trained_on": f"{sales['transaction_date'].min()} to {sales['transaction_date'].max()}",
        "n_baskets": n_baskets,
        "menu": menu,
        "popularity": dict(item_counts.most_common()),
        "popularity_by_daypart": {part: dict(counts.most_common()) for part, counts in daypart_counts.items()},
        "co_occurrence": co_occurrence(n_baskets, item_counts, pair_counts),
        "cold_start_proxies": content_proxies(menu, set(item_counts)),
    }


def main():
    menu = load_menu()
    sales = load_sales(menu)
    model = train(sales, menu)
    OUTPUT_FILE.write_text(json.dumps(model, indent=1), encoding="utf-8")

    print(f"Trained on {model['n_baskets']} baskets ({model['trained_on']})")
    print(f"Items with sales history: {len(model['popularity'])}/{len(menu)}")
    for name, proxy in model["cold_start_proxies"].items():
        print(f"  cold start: {name} -> {proxy['proxy']} ({proxy['source']})")
    print(f"Wrote {OUTPUT_FILE.relative_to(API_DIR)}")


if __name__ == "__main__":
    main()
