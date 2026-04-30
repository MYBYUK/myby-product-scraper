import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

# 1. الإعدادات - بدّل هاد بالـ ID تبع شيتك
SHEET_ID = '1BwKw3oMkXvkuLRIDDwal58Mv5ilia7zgrwiltECWxkw'

# 2. تجهيز الاتصال بـ Google Sheets
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

# بجيب الـ credentials من GitHub Secrets
creds_json = os.environ['GDRIVE_CREDS']
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# بفتح الشيت بالـ ID - أضمن من الاسم
sheet = client.open_by_key(SHEET_ID).sheet1

# 3. سكراب المنتجات من Halalo
BASE_URL = 'https://halalo.co.uk'
COLLECTION_URL = f'{BASE_URL}/collections/madinah-online'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_all_product_links():
    """بجيب كل روابط المنتجات من كل الصفحات"""
    all_links = []
    page = 1

    while True:
        url = f'{COLLECTION_URL}?page={page}'
        print(f'Checking page {page}...')

        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f'Error fetching page {page}: {e}')
            break

        soup = BeautifulSoup(res.text, 'lxml')
        products = soup.select('a.product-item__title')

        if not products:
            print('No more products found.')
            break

        for product in products:
            link = BASE_URL + product['href']
            all_links.append(link)

        page += 1
        time.sleep(1) # عشان ما نضغط ع السيرفر

    return list(set(all_links)) # بحذف التكرار

def scrape_product(url):
    """بجيب تفاصيل منتج واحد"""
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')

        # اسم المنتج
        name = soup.select_one('h1.product-meta__title')
        name = name.text.strip() if name else 'N/A'

        # السعر
        price = soup.select_one('span.price')
        price = price.text.strip().replace('\n', '') if price else 'N/A'

        # SKU
        sku = soup.select_one('span.product-meta__sku')
        sku = sku.text.strip().replace('SKU:', '').strip() if sku else 'N/A'

        # الصورة
        img = soup.select_one('img.product-gallery__image')
        img_url = 'https:' + img['src'] if img and img.get('src') else 'N/A'

        return [name, price, sku, img_url, url]

    except Exception as e:
        print(f'Error scraping {url}: {e}')
        return None

# 4. تشغيل السكريبت
print('Starting scrape from Halalo...')
product_links = get_all_product_links()
print(f'Found {len(product_links)} products on site')

scraped_data = []
for i, link in enumerate(product_links, 1):
    data = scrape_product(link)
    if data:
        scraped_data.append(data)
        print(f'Scraped {i}/{len(product_links)}: {data[0]}')
    time.sleep(0.5)

print(f'\nTotal products scraped: {len(scraped_data)}')

# 5. رفع البيانات على Google Sheets
print('Updating Google Sheet...')
sheet.clear() # بمسح الشيت القديم
sheet.append_row(['Name', 'Price', 'SKU', 'Image URL', 'Product URL']) # الهيدر

if scraped_data:
    sheet.append_rows(scraped_data) # بضيف كل المنتجات مرة وحدة - أسرع

print(f'✅ Done! Updated Google Sheet with {len(scraped_data)} products')
