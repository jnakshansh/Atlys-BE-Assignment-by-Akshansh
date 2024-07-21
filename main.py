from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import json
import os
import time
import redis

# Initialize FastAPI app
app = FastAPI()

# Basic Authentication setup
security = HTTPBasic()

# Redis setup for caching
redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0)

# Static token for simplicity
STATIC_TOKEN = "mysecrettoken"

# Define the data model for scraped product
class Product(BaseModel):
    product_title: str
    product_price: float
    path_to_image: str

# Path to store the scraped data
DATA_FILE = "scraped_data.json"

# Authentication function
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.password != STATIC_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials

# Helper function to scrape a page
def scrape_page(url, proxy=None):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    response = requests.get(url, headers=headers, proxies=proxies)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    products = []

    # Find product elements and extract data
    for product in soup.find_all('div', class_='product-inner'):
        title = product.find('h2', class_='woo-loop-product__title').text.strip()
        # print(title)
        price = product.find('span', class_='woocommerce-Price-amount').text.strip()
        # print(price)
        image_url = product.find('img', class_='attachment-woocommerce_thumbnail')['data-lazy-src']
        # print(image_url)
        # Convert price to float
        price = float(price.replace('₹', '').replace(',', ''))

        # Download and save the image
        image_path = f"images/{title}.jpg"
        image_data = requests.get(image_url).content
        with open(image_path, 'wb') as handler:
            handler.write(image_data)

        products.append(Product(product_title=title, product_price=price, path_to_image=image_path))
    
    return products

# Route to scrape products
@app.post("/scrape", dependencies=[Depends(authenticate)])
def scrape_catalogue(pages: Optional[int] = 5, proxy: Optional[str] = None):
    base_url = "https://dentalstall.com/shop/page/{}/"
    all_products = []

    for page in range(1, pages + 1):
        url = base_url.format(page)
        retry_count = 0
        while retry_count < 3:
            try:
                products = scrape_page(url, proxy)
                print(products)
                all_products.extend(products)
                break
            except requests.exceptions.RequestException as e:
                retry_count += 1
                time.sleep(3)
                if retry_count == 3:
                    print(f"Failed to scrape {url} after 3 retries.")

    # Load existing data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            existing_data = json.load(file)
    else:
        existing_data = []

    # Cache results and update if necessary
    updated_products = 0
    for product in all_products:
        cache_key = f"product:{product.product_title}"
        # cached_price = redis_client.get(cache_key)
        # if cached_price is None or float(cached_price) != product.product_price:
        #     redis_client.set(cache_key, product.product_price)
        #     existing_data.append(product.dict())
        try:
            cached_price = redis_client.get(cache_key)
            if cached_price is None or float(cached_price) != product.product_price:
                redis_client.set(cache_key, product.product_price)
                existing_data.append(product.dict())
                updated_products += 1
        except redis.exceptions.ConnectionError as e:
            print(f"Redis connection error: {e}")
            continue

    # Save updated data to JSON file
    with open(DATA_FILE, 'w') as file:
        json.dump(existing_data, file, indent=4)

    # print(f"Scraped {len(all_products)} products.")
    # return {"message": f"Scraped {len(all_products)} products."}
    print(f"Scraped {len(all_products)} products, {updated_products} updated.")
    return {"message": f"Scraped {len(all_products)} products, {updated_products} updated."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
