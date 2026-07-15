from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from PIL import Image
import imagehash
import io
import uvicorn
from typing import List

app = FastAPI(title="Zero-Cost Image Matcher for n8n")

# Browser-like headers so Facebook CDN doesn't block us
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

class Product(BaseModel):
    sku: str
    image_url: str

class MatchRequest(BaseModel):
    customer_image_url: str
    products: List[Product]

def get_image_hash(url: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content)).convert('RGB')
        return imagehash.phash(img)
    except Exception as e:
        print(f"Error processing image {url}: {e}")
        return None

@app.post("/match-image")
def match_image(req: MatchRequest):
    customer_hash = get_image_hash(req.customer_image_url)
    if not customer_hash:
        # Graceful fallback — don't crash, just return no match
        return {"matched": False, "sku": None, "difference": 999, "note": "Could not download customer image"}

    best_match = None
    lowest_diff = float('inf')
    THRESHOLD = 15

    for product in req.products:
        prod_hash = get_image_hash(product.image_url)
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
