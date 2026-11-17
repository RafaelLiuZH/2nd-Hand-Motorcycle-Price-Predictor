import os
import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import random

# Global headers to prevent HTTP 403 blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.8891.com.tw/",
}

def parse_price(raw_price_str):
    """
    Parses Taiwanese listing prices (e.g., '2.0萬', '85萬', '$50,000') into pure TWD integers.
    """
    if not raw_price_str:
        return None
    
    raw_price_str = raw_price_str.replace(" ", "").replace(",", "")
    
    # Matches numbers with optional decimal point followed by '萬'
    wan_match = re.search(r"([\d\.]+)萬", raw_price_str)
    if wan_match:
        val = float(wan_match.group(1))
        return int(val * 10000)
    
    # Matches direct numbers
    digits_match = re.search(r"\d+", raw_price_str)
    if digits_match:
        return int(digits_match.group(0))
        
    return None


def parse_vehicle_card(item, category="motorcycle"):
    """
    Extracts attributes from a single card container (<div class="scb-item">).
    """
    # 1. Full Title / Link
    title_tag = item.select_one(".text-box a") or item.select_one("a.title")
    title = title_tag.get_text(strip=True) if title_tag else None
    url = f"https://www.8891.com.tw{title_tag['href']}" if title_tag and title_tag.has_attr('href') else None

    # 2. Brand and Model (2nd <li> inside .text-box ul)
    brand_model_tag = item.select_one(".text-box ul > li:nth-of-type(2)")
    raw_brand_model = brand_model_tag.get_text(strip=True) if brand_model_tag else None
    
    brand, model = None, None
    if raw_brand_model and "," in raw_brand_model:
        brand, model = raw_brand_model.split(",", 1)
    elif raw_brand_model:
        brand = raw_brand_model

    # 3. Price
    price_tag = item.select_one(".scb-price")
    raw_price = price_tag.get_text(strip=True) if price_tag else None
    clean_price_twd = parse_price(raw_price)

    # 4. Manufacturing Year
    year_tag = item.select_one(".scb-year")
    year_str = year_tag.get_text(strip=True) if year_tag else None
    clean_year = int(re.search(r"\d{4}", year_str).group()) if year_str and re.search(r"\d{4}", year_str) else None

    # 5. Gas / Displacement (e.g., 0.1L / 125cc / 2.0L)
    gas_tag = item.select_one(".scb-gas")
    gas = gas_tag.get_text(strip=True) if gas_tag else None

    # 6. Region / City (e.g., 台中市)
    region_tag = item.select_one(".scb-region")
    region = region_tag.get_text(strip=True) if region_tag else None

    return {
        "category": category,
        "title": title,
        "brand": brand,
        "model": model,
        "price_twd": clean_price_twd,
        "year": clean_year,
        "gas_displacement": gas,
        "region": region,
        "raw_price": raw_price,
        "url": url,
    }


def scrape_8891(category="motorcycle", max_pages=3):
    """
    Crawls 8891 listings for motorcycles or cars across multiple pages.
    """
    base_url = (
        "https://www.8891.com.tw/usedauto-moto.html"
        if category == "motorcycle"
        else "https://www.8891.com.tw/usedauto-index.html"
    )
    
    all_records = []
    print(f"=== Starting 8891 Scraper [{category.upper()}] ===")

    for page in range(1, max_pages + 1):
        target_url = f"{base_url}?page={page}"
        print(f"Fetching Page {page}/{max_pages}: {target_url}")

        try:
            response = requests.get(target_url, headers=HEADERS, timeout=10)
            
            if response.status_code != 200:
                print(f"Warning: Page {page} returned HTTP status {response.status_code}. Skipping.")
                continue

            # Pass raw bytes (response.content) + 'lxml' to handle Chinese charset safely
            soup = BeautifulSoup(response.content, "lxml")
            
            # Find all card wrappers
            cards = soup.select(".scb-item")
            print(f" -> Found {len(cards)} listings on page {page}.")

            if not cards:
                print("No more listing cards found. Ending loop.")
                break

            for item in cards:
                record = parse_vehicle_card(item, category=category)
                all_records.append(record)

            # When scraping hundreds of pages, websites can temporarily block your IP (HTTP 403 or CAPTCHA) 
            # if requests are sent too fast. Add random sleep intervals to mimic human behavior
            time.sleep(random.uniform(2.5, 5.0))

        except Exception as e:
            print(f"An error occurred while fetching page {page}: {e}")

    df = pd.DataFrame(all_records)
    return df


if __name__ == "__main__":
    # Scrape Motorcycles (First 2 Pages)
    moto_df = scrape_8891(category="motorcycle", max_pages=50)
    moto_df.to_csv("8891_motorcycles.csv", index=False, encoding="utf-8-sig")
    print(f"Saved {len(moto_df)} motorcycle records to 8891_motorcycles.csv")

    # Scrape Cars (First 2 Pages)
    car_df = scrape_8891(category="car", max_pages=50)
    car_df.to_csv("8891_cars.csv", index=False, encoding="utf-8-sig")
    print(f"Saved {len(car_df)} car records to 8891_cars.csv")
