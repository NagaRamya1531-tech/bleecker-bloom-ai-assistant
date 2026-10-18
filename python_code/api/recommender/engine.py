"""Recommendation engine: basket complements, daypart popularity, cold start, and filters.

Pure Python over the trained recommender.json, with no LLM calls, so results are
deterministic, fast, and testable. The Recommendation Agent decides *what* to
ask for (items, categories, dietary needs, budget) and this engine decides
*which* items to suggest and *why*.
"""
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
import json

from .train import daypart

# Dietary needs the engine understands, as predicates over a menu item.
DIETARY_FILTERS = {
    "vegan": lambda item: "vegan" in item["tags"],
    "dairy-free": lambda item: "contains-dairy" not in item["tags"],
    "nut-free": lambda item: "contains-nuts" not in item["tags"],
    "gluten-free": lambda item: "gluten-free" in item["tags"],
    "low-caffeine": lambda item: "contains-caffeine" not in item["tags"],
    "caffeine-free": lambda item: "caffeine-free" in item["tags"],
    "sugar-free": lambda item: "sugar-free" in item["tags"],
}

DRINK_CATEGORIES = {"Espresso Drinks", "Brewed Coffee", "Cold Coffee", "Tea & Tea Lattes", "Hot Chocolate & Steamers"}
COLD_START_DISCOUNT = 0.5
MAX_PER_CATEGORY = 2


@dataclass
class Recommendation:
    name: str
    category: str
    price: float
    description: str
    reason: str
    score: float

    def to_dict(self):
        return asdict(self)


class Recommender:
    def __init__(self, model):
        self.model = model
        self.menu = model["menu"]
        self.co_occurrence = model["co_occurrence"]
        self.proxies = model["cold_start_proxies"]

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as model_file:
            return cls(json.load(model_file))

    @property
    def categories(self):
        return sorted({item["category"] for item in self.menu.values()})

    def is_allowed(self, name, categories=None, dietary=None, max_price=None):
        item = self.menu[name]
        if categories and item["category"] not in categories:
            return False
        if max_price is not None and item["price"] > max_price:
            return False
        return all(DIETARY_FILTERS[need](item) for need in dietary or [] if need in DIETARY_FILTERS)

    def _recommendation(self, name, reason, score):
        item = self.menu[name]
        return Recommendation(name, item["category"], item["price"], item["description"], reason, round(score, 4))

    def _rules_for(self, name):
        """Co-occurrence rules for an item, borrowing its proxy's rules on cold start."""
        if name in self.co_occurrence:
            return self.co_occurrence[name], None
        if name in self.proxies:
            proxy = self.proxies[name]["proxy"]
            return self.co_occurrence.get(proxy, []), proxy
        return [], None

    def _take_diverse(self, scored, top_k, exclude=(), categories=None):
        """Highest scores first, at most MAX_PER_CATEGORY per category
        (no cap when the customer asked for specific categories)."""
        max_per_category = top_k if categories else MAX_PER_CATEGORY
        chosen, per_category = [], Counter()
        for recommendation in sorted(scored, key=lambda r: r.score, reverse=True):
            if recommendation.name in exclude or any(r.name == recommendation.name for r in chosen):
                continue
            if per_category[recommendation.category] >= max_per_category:
                continue
            chosen.append(recommendation)
            per_category[recommendation.category] += 1
            if len(chosen) == top_k:
                break
        return chosen

    def popular(self, top_k=3, categories=None, dietary=None, max_price=None, part=None):
        """Most popular items, for the current daypart when given."""
        counts = self.model["popularity_by_daypart"].get(part) or self.model["popularity"]
        label = f"popular in the {part}" if part in self.model["popularity_by_daypart"] else "one of our most popular items"
        scored = []
        for name in self.menu:
            if not self.is_allowed(name, categories, dietary, max_price):
                continue
            count = counts.get(name, 0)
            reason = label
            if not count:
                # Items with no sales history rank below every item that has sales (we don't invent
                # popularity), ordered among themselves by their similar item's popularity.
                proxy = self.proxies.get(name, {})
                count = counts.get(proxy.get("proxy"), 0) * proxy.get("similarity", 0) * 1e-6
                reason = "new on our menu"
            scored.append(self._recommendation(name, reason, count))
        return self._take_diverse(scored, top_k, categories=categories)

    def complements(self, cart, top_k=3, categories=None, dietary=None, max_price=None,
                    score_by="confidence", min_lift=0.0, fill=True, part=None, one_drink=True):
        """Items frequently bought with the cart items.

        score_by: "confidence" (share of baskets with the cart item that also had
        this item) or "lift" (how much more likely than chance). Confidence won
        the offline eval (see recommender/evaluate.py); lift over-rewards rare pairs.
        fill: top up with popular items when there are too few strong pairings.
        one_drink: if the cart already has a drink, suggest food and add-ons rather than a
        second drink (unless the customer asked for a drink category).
        """
        cart = [name for name in cart if name in self.menu]
        # Don't suggest what's effectively already in the cart, e.g. Brazilian Organic Drip
        # for a Cold Brew (same beans, and the Cold Brew's stand-in item).
        exclude = set(cart) | {self.proxies[name]["proxy"] for name in cart if name in self.proxies}
        if one_drink and not categories and any(self.menu[name]["category"] in DRINK_CATEGORIES for name in cart):
            exclude |= {name for name, item in self.menu.items() if item["category"] in DRINK_CATEGORIES}
        scored = {}
        for cart_item in cart:
            rules, proxy = self._rules_for(cart_item)
            discount = COLD_START_DISCOUNT if proxy else 1.0
            for rule in rules:
                if rule["lift"] < min_lift:
                    continue
                score = rule[score_by] * discount
                if proxy:
                    reason = f"{cart_item} is new, so this is based on orders of the similar {proxy}"
                elif rule["confidence"] >= 0.05:
                    reason = f"ordered with the {cart_item} in {rule['confidence']:.0%} of {cart_item} orders"
                else:
                    reason = f"sometimes ordered with the {cart_item}"
                candidates = [rule["item"]]
                if not proxy:
                    # New items inherit their stand-in's pairings at a discount, but only one hop:
                    # a guess based on a guess (new cart item -> new suggestion) is too weak to show.
                    candidates += [name for name, info in self.proxies.items() if info["proxy"] == rule["item"]]
                for name in candidates:
                    candidate_score = score if name == rule["item"] else score * COLD_START_DISCOUNT
                    if name in exclude or not self.is_allowed(name, categories, dietary, max_price):
                        continue
                    if name not in scored or candidate_score > scored[name].score:
                        candidate_reason = reason if name == rule["item"] else \
                            f"new on our menu and similar to the {rule['item']}, which is often ordered with the {cart_item}"
                        scored[name] = self._recommendation(name, candidate_reason, candidate_score)

        chosen = self._take_diverse(list(scored.values()), top_k, exclude=exclude, categories=categories)
        if fill and len(chosen) < top_k:
            extra = self.popular(top_k + len(cart) + len(chosen) + MAX_PER_CATEGORY * 4,
                                 categories, dietary, max_price, part)
            chosen = self._take_diverse(chosen + [
                Recommendation(**{**r.to_dict(), "score": -1 - i}) for i, r in enumerate(extra)
            ], top_k, exclude=exclude, categories=categories)
        return chosen

    def recommend(self, cart=None, top_k=3, categories=None, dietary=None, max_price=None, now=None):
        part = daypart((now or datetime.now()).hour)
        if cart:
            return self.complements(cart, top_k, categories, dietary, max_price, part=part)
        return self.popular(top_k, categories, dietary, max_price, part)
