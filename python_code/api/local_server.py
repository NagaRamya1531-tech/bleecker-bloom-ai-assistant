import json
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent_controller import AgentController
from agents.menu import price_order
from sessions import AuthError, build_session_store, now_ms


ROOT_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_FILE = ROOT_DIR / "products" / "products.jsonl"
PRODUCT_IMAGES_DIR = ROOT_DIR / "products" / "images"
APP_IMAGES_DIR = ROOT_DIR.parent / "coffee_shop_app" / "assets" / "images"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/product-images",
    StaticFiles(directory=str(PRODUCT_IMAGES_DIR)),
    name="product-images",
)
app.mount(
    "/app-images",
    StaticFiles(directory=str(APP_IMAGES_DIR)),
    name="app-images",
)
agent_controller = AgentController()
session_store = build_session_store()


class OrderItem(BaseModel):
    item: str = Field(max_length=100)
    quantity: int = Field(ge=1, le=20)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    cart: list[OrderItem] | None = Field(default=None, max_length=50)


class OrderRequest(BaseModel):
    items: list[OrderItem] = Field(max_length=50)


def current_user(authorization: str | None = Header(default=None),
                 x_device_id: str | None = Header(default=None)):
    """The customer's id: a verified Supabase user id, or a device id in local development."""
    try:
        return session_store.identify(authorization, x_device_id)
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.post("/")
def chat(payload: dict):
    """Stateless endpoint (same shape as RunPod): the client sends the whole conversation."""
    return {"output": agent_controller.get_response(payload)}


@app.get("/health")
def health():
    return {"status": "ok", "session_store": session_store.name}


@app.get("/chat")
def get_conversation(uid: str = Depends(current_user)):
    """The customer's saved conversation, so the app can restore it on any screen or after a restart."""
    return {"messages": session_store.load_messages(uid)}


@app.post("/chat")
def send_message(request: ChatRequest, uid: str = Depends(current_user)):
    """Stateful chat: the server keeps the conversation, so the app only sends the new message."""
    messages = session_store.load_messages(uid) + [{"role": "user", "content": request.message.strip()}]
    cart = [item.model_dump() for item in request.cart] if request.cart is not None else None
    reply = agent_controller.get_response({"input": {"messages": messages, "cart": cart}})
    session_store.save_messages(uid, messages + [reply])
    return {"output": reply}


@app.delete("/chat")
def reset_conversation(uid: str = Depends(current_user)):
    session_store.clear_messages(uid)
    return {"status": "cleared"}


@app.post("/orders")
def place_order(request: OrderRequest, uid: str = Depends(current_user)):
    """Record an order with prices recomputed from the menu, then start a fresh conversation."""
    items = price_order([item.model_dump() for item in request.items])
    if not items:
        raise HTTPException(status_code=400, detail="The order has no menu items")
    order = {"items": items, "total": round(sum(item["price"] for item in items), 2), "created_at": now_ms()}
    order_id = session_store.add_order(uid, order)
    session_store.clear_messages(uid)
    return {"id": order_id, **order}


@app.get("/orders")
def recent_orders(uid: str = Depends(current_user)):
    return {"orders": session_store.recent_orders(uid)}


@app.get("/products")
def products(request: Request):
    base_url = str(request.base_url).rstrip("/")
    result = []
    with PRODUCTS_FILE.open(encoding="utf-8") as products_file:
        for line in products_file:
            product = json.loads(line)
            image_path = product.pop("image_path", "")
            product["id"] = product["name"]
            if image_path.startswith("app:"):
                product["image_url"] = f"{base_url}/app-images/{quote(image_path[4:])}"
            else:
                product["image_url"] = f"{base_url}/product-images/{quote(image_path)}" if image_path else ""
            result.append(product)
    return result