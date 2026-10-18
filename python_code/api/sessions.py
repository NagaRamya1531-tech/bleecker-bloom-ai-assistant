"""Server-side conversations and orders, stored in Supabase (Postgres).

The API is the only writer, so the conversation (including the cart in
`memory.order`) can't be edited by the app. Each customer is identified by a
Supabase access token from anonymous sign-in, verified with Supabase Auth, so
nobody can read another customer's chat.

Tables (see supabase/schema.sql; Row Level Security blocks app access):
    chats  (user_id uuid primary key, messages jsonb, updated_at timestamptz)
    orders (id uuid, user_id uuid, items jsonb, total numeric, created_at timestamptz)

When SUPABASE_URL and SUPABASE_SECRET_KEY are not set (local development), an
in-memory store is used and the app identifies itself with a random device id.
"""
from datetime import datetime, timezone
import os
import re
import threading
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

MAX_STORED_MESSAGES = 60
DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{16,64}$")
TOKEN_CACHE_SECONDS = 60


class AuthError(Exception):
    pass


def now_ms():
    return int(time.time() * 1000)


class InMemorySessionStore:
    """For local development: lost when the server restarts."""
    name = "memory"

    def __init__(self):
        self.chats, self.orders = {}, {}
        self.lock = threading.Lock()

    def identify(self, authorization, device_id):
        if not device_id or not DEVICE_ID_PATTERN.match(device_id):
            raise AuthError("Missing or invalid X-Device-Id header")
        return f"device-{device_id}"

    def load_messages(self, uid):
        with self.lock:
            return list(self.chats.get(uid, []))

    def save_messages(self, uid, messages):
        with self.lock:
            self.chats[uid] = list(messages[-MAX_STORED_MESSAGES:])

    def clear_messages(self, uid):
        with self.lock:
            self.chats.pop(uid, None)

    def add_order(self, uid, order):
        with self.lock:
            order_id = f"order-{now_ms()}"
            self.orders.setdefault(uid, {})[order_id] = order
            return order_id

    def recent_orders(self, uid, limit=5):
        with self.lock:
            orders = sorted(self.orders.get(uid, {}).items(), key=lambda item: item[1]["created_at"])
            return [{"id": order_id, **order} for order_id, order in orders[-limit:]]


class SupabaseSessionStore:
    """Talks to Supabase's REST (PostgREST) and Auth APIs with the server-only secret key."""
    name = "supabase"

    def __init__(self, url, secret_key, client=None):
        self.url = url.rstrip("/")
        headers = {"apikey": secret_key, "Content-Type": "application/json"}
        # Legacy service_role keys are JWTs and also go in Authorization; new sb_secret_ keys must not.
        if secret_key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {secret_key}"
        self.client = client or httpx.Client(base_url=self.url, headers=headers, timeout=20)
        self.secret_key = secret_key
        self.token_cache = {}
        self.lock = threading.Lock()

    def _check(self, response):
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase {response.request.method} {response.request.url.path} "
                               f"failed: {response.status_code} {response.text[:200]}")
        return response

    def identify(self, authorization, device_id):
        token = (authorization or "").removeprefix("Bearer ").strip()
        if not token:
            raise AuthError("Missing Supabase access token")
        with self.lock:
            cached = self.token_cache.get(token)
            if cached and cached[1] > time.time():
                return cached[0]
        # Supabase Auth checks the signature and expiry and returns the user.
        response = self.client.get("/auth/v1/user", headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200 or not response.json().get("id"):
            raise AuthError(f"Invalid Supabase access token ({response.status_code})")
        uid = response.json()["id"]
        with self.lock:
            if len(self.token_cache) > 10_000:
                self.token_cache.clear()
            self.token_cache[token] = (uid, time.time() + TOKEN_CACHE_SECONDS)
        return uid

    def load_messages(self, uid):
        response = self._check(self.client.get("/rest/v1/chats", params={"user_id": f"eq.{uid}", "select": "messages"}))
        rows = response.json()
        return rows[0]["messages"] if rows else []

    def save_messages(self, uid, messages):
        self._check(self.client.post(
            "/rest/v1/chats",
            params={"on_conflict": "user_id"},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            json={"user_id": uid, "messages": messages[-MAX_STORED_MESSAGES:],
                  "updated_at": datetime.now(timezone.utc).isoformat()},
        ))

    def clear_messages(self, uid):
        self._check(self.client.delete("/rest/v1/chats", params={"user_id": f"eq.{uid}"}))

    def add_order(self, uid, order):
        response = self._check(self.client.post(
            "/rest/v1/orders",
            headers={"Prefer": "return=representation"},
            json={"user_id": uid, "items": order["items"], "total": order["total"],
                  "created_at": datetime.fromtimestamp(order["created_at"] / 1000, timezone.utc).isoformat()},
        ))
        return response.json()[0]["id"]

    def recent_orders(self, uid, limit=5):
        response = self._check(self.client.get("/rest/v1/orders", params={
            "user_id": f"eq.{uid}", "select": "id,items,total,created_at",
            "order": "created_at.desc", "limit": limit,
        }))
        orders = [{**row, "total": float(row["total"]),
                   "created_at": int(datetime.fromisoformat(row["created_at"]).timestamp() * 1000)}
                  for row in response.json()]
        return sorted(orders, key=lambda order: order["created_at"])


def build_session_store():
    url, secret_key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY")
    if url and secret_key:
        return SupabaseSessionStore(url, secret_key)
    return InMemorySessionStore()
