import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

SHEET_ID = '1BwKw3oMkXvkuLRIDDwal58Mv5ilia7zgrwiltECWxkw'
BASE_URL = 'https://halalo.co.uk'
CATEGORY_URL = f'{BASE_URL}/index.php?dispatch=companies.view&company_id=3&scroller_id=category_1127'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds_json = os.environ['GDRIVE_CREDS']
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

def get_all_product_links():
    all_links = []
    page = 1
    while True:
        if page == 1:
            url = CATEGORY_URL
        else:
            url = f'{CATEGORY_URL}&page={page}'
        print(f'Checking page {page}... {url}')
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
        except:
            break
        soup = BeautifulSoup(res.text, 'lxml')
        products = soup.select('a.product-title')
        if not products:
            break
        for product in products:
            link = product['href']
            if not link.startswith('http'):
                link = BASE_URL + '/' + link.lstrip('/')
            all_links.append(link)
        page += 1
        time.sleep(1)
    return list(set(all_links))

def scrape_product(url, debug=False):
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')

        # --- DEBUG: بطبع أول منتج عشان نشوف السيلكتورز ---
        if debug:
            print("\n=== DEBUG: HTML for first product ===")
            print("H1:", soup.select_one('h1'))
            print("Price spans:", soup.select('span[class*="price"]')[:3])
            print("SKU spans:", soup.select('span[id*="product_code"]'))
            print("Images:", soup.select('img[class*="ty-pict"]')[:2])
            print("=== END DEBUG ===\n")

        # 1. اسم المنتج
        name = soup.find('h1')
        name = name.text.strip() if name else 'N/A'

        # 2. السعر - بجرب كل الاحتمالات
        price = None
        for sel in ['span.ty-price-num', 'span[id*="sec_discounted_price"]', 'span[id*="price"]', '.ty-price']:
            price = soup.select_one(sel)
            if price:
                price = price.text.strip()
                break
        if not price:
            price = 'N/A'
        if price!= 'N/A' and '£' not in price:
            price = '£' + price

        # 3. SKU
        sku = None
        for sel in ['span.ty-product-block__sku-code', 'span[id*="product_code"]', '.ty-control-group:contains("SKU") span']:
            sku = soup.select_one(sel)
            if sku:
                sku = sku.text.strip()
                break
        if not sku:
            sku = 'N/A'

        # 4. الصورة
        img = None
        for sel in ['img.ty-pict[id*="det_img"]', 'a.cm-image-previewer img', '.ty-product-img img']:
            img = soup.select_one(sel)
            if img and img.get('src'):
                img_url = img['src']
                if not img_url.startswith('http'):
                    img_url = BASE_URL + img_url
                break
        if not img:
            img_url = 'N/A'

        return [name, price, sku, img_url, url]

    except Exception as e:
        print(f'Error scraping {url}: {e}')
        return None

print('Starting scrape from Halalo...')
product_links = get_all_product_links()
print(f'Found {len(product_links)} products on site')

scraped_data = []
for i, link in enumerate(product_links, 1):
    # بطبع Debug لأول منتج بس
    data = scrape_product(link, debug=(i==1))
    if data:
        scraped_data.append(data)
        print(f'Scraped {i}/{len(product_links)}: {data[0]} | {data[1]} | {data[2]}')
    time.sleep(0.5)

print(f'\nTotal products scraped: {len(scraped_data)}')

print('Updating Google Sheet...')
sheet.clear()
sheet.append_row(['Name', 'Price', 'SKU', 'Image URL', 'Product URL'])
if scraped_data:
    sheet.append_rows(scraped_data)
print(f'✅ Done! Updated Google Sheet with {len(scraped_data)} products')
