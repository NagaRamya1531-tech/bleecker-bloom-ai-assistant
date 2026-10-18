import os
from .utils import get_chatbot_response, parse_json_output
from openai import OpenAI
from copy import deepcopy
from dotenv import load_dotenv
from recommender.engine import DIETARY_FILTERS, Recommender
load_dotenv()

CATEGORY_NOUNS = {"Espresso Drinks": "espresso drinks", "Brewed Coffee": "brewed coffees",
                  "Cold Coffee": "cold coffees", "Tea & Tea Lattes": "teas",
                  "Hot Chocolate & Steamers": "hot chocolates or steamers", "Bakery": "pastries",
                  "Breakfast & Lunch": "breakfast or lunch items", "Add-ons": "add-ons"}
ALLERGY_NEEDS = {"nut-free", "dairy-free", "gluten-free", "vegan"}


class RecommendationAgent():
    """Turns a customer request into structured constraints, asks the recommender
    engine for items, and phrases the result. The LLM never picks the items itself."""

    def __init__(self,recommender_path):
        self.client = OpenAI(
            api_key=os.getenv("RUNPOD_TOKEN"),
            base_url=os.getenv("RUNPOD_CHATBOT_URL"),
        )
        self.model_name = os.getenv("MODEL_NAME")
        self.recommender = Recommender.load(recommender_path)
        self.products = list(self.recommender.menu)

    def find_products_in_text(self,text):
        text = text.lower()
        # Longest names first so "Chocolate Croissant" is not also matched as "Croissant".
        found = []
        for product in sorted(self.products, key=len, reverse=True):
            if product.lower() in text:
                found.append(product)
                text = text.replace(product.lower(), " ")
        return found

    def last_order_items(self,messages):
        for message in reversed(messages):
            order = message.get("memory", {}).get("order") if message["role"] == "assistant" else None
            if order:
                return self.normalize_items([item["item"] for item in order])
        return []

    def normalize_items(self,names):
        """Map free-text item names onto exact menu names, dropping anything not on the menu."""
        return [match for name in names for match in self.find_products_in_text(str(name))][:5]

    def extract_request(self,messages):
        system_prompt = f"""You extract what a coffee shop customer wants recommendations for.

Menu items: {", ".join(self.products)}
Categories: {", ".join(self.recommender.categories)}
Dietary needs: {", ".join(DIETARY_FILTERS)}

Return a JSON object with these keys:
"items": menu items the customer has, is ordering, or wants something to go with (exact names from the menu items list), or [].
"categories": categories the customer explicitly asked for, e.g. "pastry" or "something sweet" means Bakery; "food", "breakfast", "lunch", or "sandwich" means Breakfast & Lunch; "coffee" means Espresso Drinks and Brewed Coffee; "iced" or "cold" coffee means Cold Coffee; "tea" or "chai" means Tea & Tea Lattes; "syrup", "flavor", or "milk" means Add-ons (exact names from the categories list). Use [] if the customer did not name a type of item; do not guess one.
"dietary": dietary needs the customer mentioned (exact values from the dietary needs list; "no caffeine" or "caffeine-free" means "caffeine-free", "less caffeine" or "low caffeine" means "low-caffeine", "lactose intolerant" means "dairy-free"), or [].
"max_price": the customer's budget per item in dollars as a number, or null.
"""
        input_messages = [{"role": "system", "content": system_prompt}] + messages[-3:]
        output = parse_json_output(get_chatbot_response(self.client,self.model_name,input_messages,json_mode=True))

        # Validate everything against the real menu; the LLM output is only a suggestion.
        items = self.normalize_items(output.get("items") or [])
        items += [item for item in self.find_products_in_text(messages[-1]["content"]) if item not in items]
        categories = [category for category in output.get("categories") or [] if category in self.recommender.categories]
        dietary = [need for need in output.get("dietary") or [] if need in DIETARY_FILTERS]
        max_price = output.get("max_price")
        max_price = float(max_price) if isinstance(max_price, (int, float)) and max_price > 0 else None
        if not items and not categories:
            # "What goes with my order?" -> use the cart from the order-taking agent.
            items = self.last_order_items(messages)
        return {"items": items, "categories": categories, "dietary": dietary, "max_price": max_price}

    def get_response(self,messages):
        messages = deepcopy(messages)
        request = self.extract_request(messages)
        recommendations = self.recommender.recommend(
            cart=request["items"],
            categories=request["categories"],
            dietary=request["dietary"],
            max_price=request["max_price"],
        )

        if not recommendations:
            nouns = " or ".join(CATEGORY_NOUNS.get(category, category) for category in request["categories"]) or "items"
            wanted = " ".join(request["dietary"] + [nouns])
            if request["max_price"]:
                wanted += f" under ${request['max_price']:.2f}"
            return self.postprocess(
                f"Sorry, we don't have any {wanted} on our menu right now. "
                "Would you like a suggestion without that restriction?",
                recommendations, request,
            )

        content = self.describe(messages, recommendations)
        if any(need in ALLERGY_NEEDS for need in request["dietary"]):
            content += ("\n\nOur kitchen also handles milk, wheat, eggs, soy, and tree nuts, so we can't guarantee "
                        "any item is free from cross-contact. Please tell your barista about severe allergies.")
        return self.postprocess(content, recommendations, request)

    def describe(self,messages,recommendations):
        facts = "\n".join(
            f"- {r.name} (${r.price:.2f}): {r.description} Why: {r.reason}."
            for r in recommendations
        )
        system_prompt = """You are a friendly barista at Bleecker & Bloom, a coffee shop.
Recommend exactly the items listed below, in that order, as a short unordered list: the item name, its price, and one short sentence on why the customer might like it, based on the "Why" note. Phrase statistics naturally (e.g. "often ordered with a latte"). Stay faithful to the "Why" note: if it says an item is new or that the suggestion is based on a similar item, do not claim it is often ordered with the customer's item. Do not add other items, prices, or facts. If the customer mentioned an allergy, do not call any item "nutty" or describe its flavor in a way that suggests the allergen. Keep the whole reply under 80 words."""
        prompt = f"""Customer message: {messages[-1]['content']}

Items to recommend:
{facts}"""
        input_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        return get_chatbot_response(self.client,self.model_name,input_messages)

    def get_recommendations_from_order(self,order,top_k=2):
        """Suggestions to append to an order confirmation (no LLM call)."""
        return self.recommender.recommend(cart=self.normalize_items([item["item"] for item in order]), top_k=top_k)

    def postprocess(self,output,recommendations=(),request=None):
        output = {
            "role": "assistant",
            "content": output,
            "memory": {"agent":"recommendation_agent",
                       "recommendations": [r.to_dict() for r in recommendations],
                       "request": request or {},
                      }
        }
        return output
