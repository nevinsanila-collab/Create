from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from PIL import Image
import imagehash
import io
import base64
import uvicorn
from typing import List, Optional

app = FastAPI(title="Zero-Cost Image Matcher for n8n")

class Product(BaseModel):
    sku: str
    image_url: str

class MatchRequest(BaseModel):
    customer_image_base64: str          # base64 string (n8n downloads from FB CDN)
    products: List[Product]

def get_image_hash_from_base64(b64_str: str):
    try:
        img_bytes = base64.b64decode(b64_str)
        img = Image.open(io.BytesIO(img_bytes))
        return imagehash.phash(img)
    except Exception as e:
        print(f"Error decoding base64 image: {e}")
        return None

def get_image_hash_from_url(url: str):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        return imagehash.phash(img)
    except Exception as e:
        print(f"Error processing image {url}: {e}")
        return None

@app.post("/match-image")
def match_image(req: MatchRequest):
    """
    Takes customer image as base64 (downloaded by n8n from FB CDN)
    and a list of product image URLs (Google Drive).
    Returns the SKU of the best matching product, or None if no match.
    """
    customer_hash = get_image_hash_from_base64(req.customer_image_base64)
    if not customer_hash:
        raise HTTPException(status_code=400, detail="Could not process customer image")

    best_match = None
    lowest_diff = float('inf')

    # Threshold: 0 = identical, <10 = very similar, <15 = similar
    THRESHOLD = 15

    for product in req.products:
        prod_hash = get_image_hash_from_url(product.image_url)
        if prod_hash:
            diff = customer_hash - prod_hash
            if diff < lowest_diff:
                lowest_diff = diff
                best_match = product.sku

    if best_match and lowest_diff <= THRESHOLD:
        return {"matched": True, "sku": best_match, "difference": lowest_diff}
    else:
        return {"matched": False, "sku": None, "difference": lowest_diff}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
