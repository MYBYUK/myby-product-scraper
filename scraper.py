import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

SHEET_ID = '1BwKw3oMkXvkuLRIDDwal58Mv5ilia7zgrwiltECWxkw'
BASE_URL = 'https://halalo.co.uk'

# كل الأقسام اللي بدك إياها
CATEGORIES = [
    'index.php?dispatch=companies.view&company_id=3&scroller_id=category_1127', # Beef & Veal
    'index.php?dispatch=companies.view&company_id=3&category_id=1139', # قسم 1 جديد
    'index.php?dispatch=companies.view&company_id=3&category_id=1277', # قسم 2 جديد
    'index.php?dispatch=companies.view&company_id=3&category_id=1133', # قسم 3 جديد
    'index.php?dispatch=companies.view&company_id=3&category_id=1284', # قسم 4 جديد
]

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

    for cat_url in CATEGORIES:
        page = 1
        cat_name = cat_url.split('=')[-1] # عشان نطبع اسم القسم باللوج
        print(f'\n--- Starting Category: {cat_name} ---')

        while True:
            if page == 1:
                url = f'{BASE_URL}/{cat_url}'
            else:
                url = f'{BASE_URL}/{cat_url}&page={page}'

            print(f'Checking page {page}...')
            try:
                res = requests.get(url, headers=headers, timeout=15)
                res.raise_for_status()
            except:
                print(f'Finished category {cat_name}')
                break

            soup = BeautifulSoup(res.text, 'lxml')
            products = soup.select('a.product-title')
            if not products:
                print(f'No more products in {cat_name}')
                break

            for product in products:
                link = product['href']
                if not link.startswith('http'):
                    link = BASE_URL + '/' + link.lstrip('/')
                all_links.append(link)

            page += 1
            time.sleep(1)

    return list(set(all_links))

def scrape_product(url):
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')

        # 1. الاسم
        name = soup.select_one('h1.ty-product-bigpicture__right-title')
        name = name.text.strip() if name else 'N/A'

        # 2. السعر
        price_container = soup.select_one('span.ty-price[id*="line_discounted_price"]')
        if price_container:
            price_parts = price_container.select('span.ty-price-num')
            price = ''.join([p.text.strip() for p in price_parts])
        else:
            price = 'N/A'

        # 3. SKU - مش موجود
        sku = 'N/A'

        # 4. صورة المنتج
        img_url = 'N/A'
        img_tags = soup.select('div.ty-product-img img, a.cm-image-previewer img')
        for img in img_tags:
            src = img.get('src', '')
            if 'logo' not in src.lower() and 'al_bayder' not in src.lower():
                img_url = src
                if not img_url.startswith('http'):
                    img_url = BASE_URL + img_url
                break

        return [name, price, sku, img_url, url]

    except Exception as e:
        print(f'Error scraping {url}: {e}')
        return None

print('Starting scrape from Halalo...')
product_links = get_all_product_links()
print(f'\nFound {len(product_links)} total products across all categories')

scraped_data = []
for i, link in enumerate(product_links, 1):
    data = scrape_product(link)
    if data:
        scraped_data.append(data)
        print(f'Scraped {i}/{len(product_links)}: {data[0]} | {data[1]}')
    time.sleep(0.5)

print(f'\nTotal products scraped: {len(scraped_data)}')

print('Updating Google Sheet...')
sheet.clear()
sheet.append_row(['Name', 'Price', 'SKU', 'Image URL', 'Product URL'])
if scraped_data:
    sheet.append_rows(scraped_data)
print(f'✅ Done! Updated Google Sheet with {len(scraped_data)} products')
