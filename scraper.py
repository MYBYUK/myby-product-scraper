import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

# 1. الإعدادات
SHEET_ID = '1BwKw3oMkXvkuLRIDDwal58Mv5ilia7zgrwiltECWxkw'
BASE_URL = 'https://halalo.co.uk'
CATEGORY_URL = f'{BASE_URL}/index.php?dispatch=companies.view&company_id=3&scroller_id=category_1127'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 2. تجهيز Google Sheets
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

creds_json = os.environ['GDRIVE_CREDS']
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

def get_all_product_links():
    """بجيب كل روابط المنتجات من كل الصفحات"""
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
        except requests.exceptions.RequestException as e:
            print(f'Error fetching page {page}: {e}')
            break

        soup = BeautifulSoup(res.text, 'lxml')
        products = soup.select('a.product-title')

        if not products:
            print('No more products found.')
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
    """بجيب تفاصيل منتج واحد - سيلكتورز معدلة لموقع Halalo CS-Cart"""
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')

        # 1. اسم المنتج
        name = soup.select_one('h1.ty-product-block-title')
        if not name:
            name = soup.select_one('h1[itemprop="name"]')
        if not name:
            name = soup.select_one('.ty-product-block__title')
        name = name.text.strip() if name else 'N/A'

        # 2. السعر
        price = soup.select_one('span.ty-price-num')
        if not price:
            price = soup.select_one('span[id*="sec_discounted_price"]')
        if not price:
            price = soup.select_one('span.ty-price')
        price = price.text.strip() if price else 'N/A'
        if price != 'N/A' and not price.startswith('£'):
            price = '£' + price

        # 3. SKU / Product Code
        sku = soup.select_one('span.ty-product-block__sku-code')
        if not sku:
            sku = soup.select_one('span[id*="product_code_update"]')
        if not sku:
            sku = soup.select_one('.ty-product-block__sku span')
        sku = sku.text.strip() if sku else 'N/A'

        # 4. الصورة الرئيسية
        img = soup.select_one('img.ty-pict[id*="det_img"]')
        if not img:
            img = soup
