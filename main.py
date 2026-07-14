from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from PIL import Image
import imagehash
import io
import uvicorn
from typing import List

app = FastAPI(title="Zero-Cost Image Matcher for n8n")

class Product(BaseModel):
    sku: str
    image_url: str

class MatchRequest(BaseModel):
    customer_image_url: str
    products: List[Product]

def get_image_hash(url: str):
    try:
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        # Compute perceptual hash (phash is good for finding visually similar images)
        return imagehash.phash(img)
    except Exception as e:
        print(f"Error processing image {url}: {e}")
        return None

@app.post("/match-image")
def match_image(req: MatchRequest):
    """
    Takes a customer uploaded image URL and a list of product image URLs.
    Returns the SKU of the best matching product, or None if no good match is found.
    """
    customer_hash = get_image_hash(req.customer_image_url)
    if not customer_hash:
        raise HTTPException(status_code=400, detail="Could not process customer image")

    best_match = None
    lowest_diff = float('inf')
    
    # Tolerance threshold for perceptual hash difference. 
    # A difference of 0 means exactly identical. < 10 is usually very similar.
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

if __name__ == "__main__":
    # Run the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
