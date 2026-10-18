"""Upload the menu and product photos to Supabase.

Photos go to the public `product-images` Storage bucket; products are upserted into the
`products` table with their public image URL. Products no longer in products.jsonl are removed.
Run supabase/schema.sql first.

Usage, from python_code/api (needs SUPABASE_URL and SUPABASE_SECRET_KEY in python_code/.env):
    python -m supabase_seed
"""
import mimetypes
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from agents.menu import load_products

load_dotenv()

BUCKET = "product-images"
ROOT_DIR = Path(__file__).resolve().parents[2]
PRODUCT_IMAGES_DIR = ROOT_DIR / "python_code" / "products" / "images"
APP_IMAGES_DIR = ROOT_DIR / "coffee_shop_app" / "assets" / "images"


def image_file(image_path):
    if not image_path:
        return None
    if image_path.startswith("app:"):
        return APP_IMAGES_DIR / image_path[4:]
    return PRODUCT_IMAGES_DIR / image_path


def main():
    url, secret_key = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SECRET_KEY"]
    headers = {"apikey": secret_key}
    if secret_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {secret_key}"
    client = httpx.Client(base_url=url, headers=headers, timeout=60)

    rows = []
    for order, product in enumerate(load_products()):
        path = image_file(product.get("image_path"))
        image_url = ""
        if path and path.exists():
            response = client.post(
                f"/storage/v1/object/{BUCKET}/{path.name}",
                content=path.read_bytes(),
                headers={"Content-Type": mimetypes.guess_type(path.name)[0] or "image/jpeg", "x-upsert": "true"},
            )
            response.raise_for_status()
            image_url = f"{url}/storage/v1/object/public/{BUCKET}/{path.name}"
        rows.append({
            "name": product["name"],
            "category": product["category"],
            "description": product["description"],
            "ingredients": product["ingredients"],
            "price": product["price"],
            "rating": product["rating"],
            "image_url": image_url,
            "sort_order": order,
        })

    client.post("/rest/v1/products", params={"on_conflict": "name"},
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"}, json=rows).raise_for_status()
    names = ",".join('"' + row["name"].replace('"', '\\"') + '"' for row in rows)
    client.delete("/rest/v1/products", params={"name": f"not.in.({names})"}).raise_for_status()
    print(f"Seeded {len(rows)} products ({sum(1 for row in rows if row['image_url'])} with photos) into Supabase")


if __name__ == "__main__":
    main()
