import json
import logging
import os
import re
from .utils import get_chatbot_response,parse_json_output
from openai import OpenAI
from copy import deepcopy
from dotenv import load_dotenv
from .menu import match_menu_item, menu_prices, menu_text, price_order
load_dotenv()

MENU_TEXT = menu_text()
MAX_QUANTITY = 20
logger = logging.getLogger(__name__)

# Short, predictable ways customers end an order; a backstop for small models that miss them.
FINISHED_PATTERN = re.compile(
    r"^\W*(?:no,?\s*)?(?:that'?s (?:all|it|everything)|that will be all|nothing (?:else|more)|i'?m (?:done|good)|"
    r"no(?:pe)?|all (?:done|set)|check ?out|done)"
    r"(?:[\s,.!]*(?:thanks?|thank you|thx|please|for now|for today))*[\s.!]*$", re.IGNORECASE)


def is_finishing(text):
    return bool(FINISHED_PATTERN.fullmatch(text.strip()))


def order_changes_schema(menu_names):
    """JSON schema for the order update: every item must be an exact menu name or "none"."""
    line = {"type": "object", "additionalProperties": False,
            "properties": {"requested": {"type": "string"},
                           "item": {"type": "string", "enum": list(menu_names) + ["none"]},
                           "quantity": {"type": "integer"}},
            "required": ["requested", "item", "quantity"]}
    changes = {"type": "array", "items": line, "maxItems": 10}
    return {"name": "order_changes", "strict": True, "schema": {
        "type": "object", "additionalProperties": False,
        "properties": {"add": changes, "remove": changes, "set": changes, "finished": {"type": "boolean"}},
        "required": ["add", "remove", "set", "finished"]}}


def parse_quantity(value, default=1):
    try:
        return min(max(int(float(value)), 0), MAX_QUANTITY)
    except (TypeError, ValueError):
        return default


def describe_items(items):
    return ", ".join(f"{quantity} {name}" for name, quantity in items)


class OrderTakingAgent():
    """Keeps the customer's cart.

    The LLM only reports what changed in the latest message (add, remove, set a quantity,
    items not on the menu, finished). Code applies the changes, prices the order from the
    menu, and writes the confirmation, so the cart and the total can't disagree.
    """

    def __init__(self, recommendation_agent):
        self.client = OpenAI(
            api_key=os.getenv("RUNPOD_TOKEN"),
            base_url=os.getenv("RUNPOD_CHATBOT_URL"),
        )
        self.model_name = os.getenv("MODEL_NAME")

        self.recommendation_agent = recommendation_agent

    def previous_state(self, messages, cart=None):
        if cart is not None:
            # The app's cart, which includes items added outside the chat; re-priced from the menu.
            asked_before = any(m.get("memory", {}).get("asked_recommendation_before")
                               for m in messages if m["role"] == "assistant")
            return price_order(cart), asked_before
        for message in reversed(messages):
            memory = message.get("memory", {}) if message["role"] == "assistant" else {}
            if "order" in memory:
                return memory.get("order") or [], memory.get("asked_recommendation_before", False)
        return [], False

    def extract_changes(self, messages, current_order, prices):
        current = json.dumps([{"item": i["item"], "quantity": i["quantity"]} for i in current_order]) if current_order else "empty"
        system_prompt = f"""You update a customer's order at Bleecker & Bloom, a coffee shop.

Menu:
{MENU_TEXT}
Current order: {current}

For each thing the customer mentions in their latest message, write what they said in "requested", the exact menu name in "item" (or "none" if it is not on the menu), and the quantity ("a latte" means 1).
Return a JSON object with these keys:
"add": new items to add.
"remove": items to take out (quantity 0 means all of them).
"set": items whose total quantity the customer states, e.g. "make it two lattes".
"finished": true only if the customer says they are done ("that's all", "nothing else", "checkout").
Only include changes from the latest message; never repeat items already in the current order unless the customer asks for more."""
        # Only the last assistant turn (so "yes, the croissant" makes sense) and the new message:
        # small models re-add items when they see the whole history.
        last_reply = next((m["content"] for m in reversed(messages[:-1]) if m["role"] == "assistant"), None)
        conversation = ([{"role": "assistant", "content": last_reply}] if last_reply else []) + \
                       [{"role": "user", "content": messages[-1]["content"]}]
        input_messages = [{"role": "system", "content": system_prompt}] + conversation
        try:
            output = get_chatbot_response(self.client, self.model_name, input_messages,
                                          json_schema=order_changes_schema(prices))
        except Exception as error:  # provider without JSON-schema support
            logger.warning("JSON schema not supported, falling back to JSON mode: %s", error)
            output = get_chatbot_response(self.client, self.model_name, input_messages, json_mode=True)
        return parse_json_output(output)

    def get_response(self,messages,cart=None):
        messages = deepcopy(messages)
        current_order, asked_recommendation_before = self.previous_state(messages, cart)
        prices = menu_prices()
        # A message that is only "that's all" can't change items, so skip the LLM call.
        changes = {} if is_finishing(messages[-1]["content"]) else self.extract_changes(messages, current_order, prices)
        if not changes and not is_finishing(messages[-1]["content"]):
            return self.postprocess("Sorry, I didn't catch that. Could you say that again?",
                                    current_order, asked_recommendation_before, finished=False)

        quantities = {item["item"]: item["quantity"] for item in current_order}
        added, updated, removed, not_on_menu = [], [], [], [str(x) for x in changes.get("not_on_menu") or [] if str(x).strip()]

        def resolve(change):
            """(menu name or None, what the customer asked for) for one change line."""
            if not isinstance(change, dict):
                return None, str(change)
            requested = str(change.get("requested") or change.get("item") or "").strip()
            item = change.get("item")
            return (None if item in (None, "", "none") else match_menu_item(item, prices)), requested

        set_names = {resolve(change)[0] for change in changes.get("set") or []}
        for change in changes.get("add") or []:
            name, requested = resolve(change)
            if not name:
                not_on_menu.append(requested)
            elif name not in set_names and (quantity := parse_quantity(change.get("quantity"))):
                quantities[name] = min(quantities.get(name, 0) + quantity, MAX_QUANTITY)
                added.append((name, quantity))
        for change in changes.get("set") or []:
            name, requested = resolve(change)
            if not name:
                not_on_menu.append(requested)
                continue
            quantities[name] = parse_quantity(change.get("quantity"), default=quantities.get(name, 1))
            updated.append((name, quantities[name]))
        for change in changes.get("remove") or []:
            name, requested = resolve(change)
            if name in quantities:
                quantity = parse_quantity(change.get("quantity"), default=0)
                taken = quantities[name] if quantity in (0, None) or change.get("quantity") == "all" \
                    else min(quantity, quantities[name])
                quantities[name] -= taken
                removed.append((name, taken))

        order = price_order([{"item": name, "quantity": quantity} for name, quantity in quantities.items() if quantity > 0])
        finished = bool(changes.get("finished")) or is_finishing(messages[-1]["content"])

        parts = []
        if added:
            parts.append(f"Added {describe_items(added)}.")
        if updated:
            parts.append(" ".join(f"Changed {name} to {quantity}." for name, quantity in updated))
        if removed:
            parts.append(f"Removed {describe_items(removed)}.")
        if not_on_menu:
            parts.append(f"Sorry, we don't have {', '.join(dict.fromkeys(x for x in not_on_menu if x))} on our menu.")
        total = sum(item["price"] for item in order)
        if finished and order:
            lines = "\n".join(f"- {item['quantity']} x {item['item']}: ${item['price']:.2f}" for item in order)
            parts.append(f"Here's your order:\n{lines}\nTotal: ${total:.2f}\n\n"
                         "Thank you! Open your bag to place the order.")
        elif finished:
            parts.append("Your order is empty. What can I get for you?")
        elif order:
            parts.append(f"Your order so far: {describe_items((i['item'], i['quantity']) for i in order)} "
                         f"(${total:.2f}). Anything else?")
        else:
            parts.append("What can I get for you today?")

        return self.postprocess(" ".join(parts), order, asked_recommendation_before, finished)

    def postprocess(self,response,order,asked_recommendation_before,finished):
        recommendations = []
        if not asked_recommendation_before and order and not finished:
            # Suggest once per conversation, after the confirmation.
            recommendations = self.recommendation_agent.get_recommendations_from_order(order)
            if recommendations:
                suggestions = " or ".join(
                    f"{'an' if r.name[0].lower() in 'aeiou' else 'a'} {r.name} (${r.price:.2f})" for r in recommendations
                )
                response += f"\n\nYou might also like {suggestions}. Would you like to add one?"
            asked_recommendation_before = True

        return {
            "role": "assistant",
            "content": response,
            "memory": {"agent":"order_taking_agent",
                       "step number": "done" if finished else "ordering",
                       "order": order,
                       "asked_recommendation_before": asked_recommendation_before,
                       "recommendations": [r.to_dict() for r in recommendations]
                      }
        }
