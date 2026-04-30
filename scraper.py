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
        # الرابط مع pagination الصح
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

        # السيلكتور الصح لمنتجات Halalo
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
    """بجيب تفاصيل منتج واحد"""
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')

        # اسم المنتج - جرب 3 احتمالات
        name = soup.select_one('h1.ty-product-block-title')
        if not name:
            name = soup.select_one('h1[itemprop="name"]')
        if not name:
            name = soup.select_one('.ty-product-block__title h1')
        name = name.text.strip() if name else 'N/A'

        # السعر - CS-Cart بستخدم ty-price-num
        price = soup.select_one('span.ty-price-num')
        if not price:
            price = soup.select_one('span[id*="sec_discounted_price"]')
        if not price:
            price = soup.select_one('.ty-price')
        price = price.text.strip() if price else 'N/A'

        # SKU / Product Code
        sku = soup.select_one('span.ty-product-block__sku-code')
        if not sku:
            sku = soup.select_one('span[id*="product_code"]')
        if not sku:
            sku = soup.select_one('.ty-control-group:contains("SKU") .ty-control-group__item')
        sku = sku.text.strip() if sku else 'N/A'

        # الصورة الرئيسية
        img = soup.select_one('img.ty-pict[id*="det_img"]')
        if not img:
            img = soup.select_one('.ty-product-img img')
        if not img:
            img = soup.select_one('a.cm-image-previewer img')
        
        if img and img.get('src'):
            img_url = img['src']
            if not img_url.startswith('http'):
                img_url = BASE_URL + img_url
        else:
            img_url = 'N/A'

        return [name, price, sku, img_url, url]

    except Exception as e:
        print(f'Error scraping {url}: {e}')
        return None

45 lines hidden
لو لسا بجيب N/A، ضيف debug عشان نشوف الـ HTML:
حط هاد الكود داخل scrape_product بعد سطر soup = BeautifulSoup... عشان نطبع أول منتج ونشوف السيلكتورز:

Python
# احذف هاي الأسطر بعد ما تزبط
if 'beef-knuckle' in url:
    print("=== DEBUG HTML ===")
    print(soup.select_one('h1'))
    print(soup.select_one('span.ty-price'))
    print(soup.select_one('span[id*="product_code"]'))
    print("=== END DEBUG ===")

2 lines hidden
شو تعمل هسا:

استبدل دالة scrape_product كاملة بالكود الأول اللي فوق
اعمل Commit → Run workflow
افتح الشيت - لازم تشوف الاسم والسعر والـ SKU والصورة كلهم موجودين
السعر رح يطلع بـ £ زي £7.34. لو بدك إياه رقم بس بدون £ قولي بعدلك إياها.

جرّب وخبرني شو طلع بالشيت.



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
sheet.clear()
sheet.append_row(['Name', 'Price', 'SKU', 'Image URL', 'Product URL'])

if scraped_data:
    sheet.append_rows(scraped_data)

print(f'✅ Done! Updated Google Sheet with {len(scraped_data)} products')
