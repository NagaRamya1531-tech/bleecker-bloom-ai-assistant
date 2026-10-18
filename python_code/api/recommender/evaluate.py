"""Offline evaluation: does the recommender predict what customers actually bought?

Time-based split: train on April 1-22, test on April 23-29. For every test
basket with 2+ menu items, hide one item and recommend from the rest; it's a
hit if the hidden item is in the top k. Every method uses the same top-k
selection (max 2 per category), so only the ranking differs.

Usage, from python_code/api:
    python -m recommender.evaluate
"""
from . import train as training
from .engine import Recommender

SPLIT_DATE = "2019-04-23"
TOP_K = 3


def train_model(sales, menu, basket_key):
    original_key = training.BASKET_KEY
    training.BASKET_KEY = basket_key
    try:
        return Recommender(training.train(sales, menu))
    finally:
        training.BASKET_KEY = original_key


def main():
    menu = training.load_menu()
    sales = training.load_sales(menu)
    train_sales = sales[sales["transaction_date"] < SPLIT_DATE]
    test_sales = sales[sales["transaction_date"] >= SPLIT_DATE]

    model = train_model(train_sales, menu, training.BASKET_KEY)
    # The original notebook's basket key, to measure the effect of the fix.
    old_key_model = train_model(train_sales, menu, ["transaction_id", "customer_id"])

    methods = {
        "popularity (overall)": lambda cart, part: model.popular(TOP_K + len(cart) + 2),
        "popularity (by daypart)": lambda cart, part: model.popular(TOP_K + len(cart) + 2, part=part),
        "confidence, old basket key": lambda cart, part: old_key_model.complements(
            cart, TOP_K, score_by="confidence", fill=False, one_drink=False),
        "confidence": lambda cart, part: model.complements(cart, TOP_K, fill=False, one_drink=False),
        "lift": lambda cart, part: model.complements(cart, TOP_K, score_by="lift", fill=False, one_drink=False),
        "confidence + daypart fill": lambda cart, part: model.complements(cart, TOP_K, part=part, one_drink=False),
        "old basket key + fill + one-drink rule": lambda cart, part: old_key_model.complements(cart, TOP_K, part=part),
        "fixed key + fill + one-drink rule (production)": lambda cart, part: model.complements(cart, TOP_K, part=part),
    }

    test_baskets = test_sales.groupby(training.BASKET_KEY).agg(
        items=("item", lambda items: sorted(set(items))), daypart=("daypart", "first"))
    test_baskets = test_baskets[test_baskets["items"].str.len() >= 2]

    hits = dict.fromkeys(methods, 0)
    trials = 0
    for items, part in zip(test_baskets["items"], test_baskets["daypart"]):
        for held_out in items:
            cart = [item for item in items if item != held_out]
            trials += 1
            for name, method in methods.items():
                top = [r.name for r in method(cart, part) if r.name not in cart][:TOP_K]
                hits[name] += held_out in top

    print(f"Train: {len(train_sales)} line items before {SPLIT_DATE}; "
          f"test: {len(test_baskets)} baskets, {trials} hide-one-item trials\n")
    print(f"{'method':<48} hit@{TOP_K}")
    for name, count in hits.items():
        print(f"{name:<48} {count / trials:6.1%}")


if __name__ == "__main__":
    main()
