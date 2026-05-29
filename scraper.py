import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

# ===== الإعدادات =====
SHEET_ID = os.environ['SHEET_ID']
BASE_URL = 'https://halalo.co.uk'

CATEGORIES = [
    'index.php?dispatch=companies.view&company_id=3&scroller_id=category_1127',
    'index.php?dispatch=companies.view&company_id=3&category_id=1139',
    'index.php?dispatch=companies.view&company_id=3&category_id=1277',
    'index.php?dispatch=companies.view&company_id=3&category_id=1133',
    'index.php?dispatch=companies.view&company_id=3&category_id=1284',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ===== Google Sheets =====
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ['GDRIVE_CREDS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet_name = os.environ.get('SHEET_NAME', 'Sheet1')
sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)


# ===== سحب روابط المنتجات =====
def get_all_product_links():
    all_links = []

    for cat_url in CATEGORIES:
        page = 1
        cat_name = cat_url.split('=')[-1]
        print(f'\n--- Starting Category: {cat_name} ---')

        while True:
            url = f'{BASE_URL}/{cat_url}' if page == 1 else f'{BASE_URL}/{cat_url}&page={page}'
            print(f'  Checking page {page}...')

            try:
                res = requests.get(url, headers=HEADERS, timeout=15)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, 'lxml')

                # المحاولة الأولى
                products = soup.select('a.product-title')

                # المحاولة الثانية
                if not products:
                    products = soup.select('h3.ty-grid-list__item-name a')

                # المحاولة الثالثة
                if not products:
                    all_anchors = soup.select('a[href]')
                    products = [
                        a for a in all_anchors
                        if a.get('href', '').startswith('https://halalo.co.uk/')
                        and a.get('href', '').count('/') >= 5
                        and 'dispatch' not in a.get('href', '')
                    ]

                if not products:
                    print(f'  No more products in category {cat_name}')
                    break

                for product in products:
                    link = product.get('href', '')
                    if link and not link.startswith('http'):
                        link = BASE_URL + '/' + link.lstrip('/')
                    if link and link not in all_links:
                        all_links.append(link)

                page += 1
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                print(f'  Network error on page {page}: {e}')
                break
            except Exception as e:
                print(f'  Unexpected error on page {page}: {e}')
                break

    return list(set(all_links))


# ===== سحب بيانات منتج واحد =====
def scrape_product(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')

        # 1. الاسم - من h1 مباشرة
        name_tag = soup.select_one('h1')
        name = name_tag.text.strip() if name_tag else 'N/A'

        # 2. السعر - يبحث عن £
        price = 'N/A'
        for tag in soup.find_all(string=lambda t: t and '£' in t):
            clean = tag.strip()
            if clean.startswith('£') and len(clean) < 15:
                price = clean
                break

        # 3. الوزن - من تفاصيل المنتج
        weight = 'N/A'
        for row in soup.select('.ty-product-feature, table tr'):
            text = row.text.strip()
            if any(unit in text for unit in ['500g', '1kg', '2kg', 'g', 'kg', 'ml', 'L']):
                weight = text.replace('\n', ' ').strip()
                break

        # 4. الصورة - من og:image
        img_tag = soup.find('meta', property='og:image')
        img_url = img_tag['content'] if img_tag else 'N/A'

        # 5. الوصف - من meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        description = desc_tag['content'] if desc_tag else 'N/A'

        print(f'  ✓ {name} | {price} | {weight}')
        return [name, price, weight, description, img_url, url]

    except requests.exceptions.RequestException as e:
        print(f'  Network error for {url}: {e}')
        return None
    except Exception as e:
        print(f'  Error scraping {url}: {e}')
        return None


# ===== التشغيل الرئيسي =====
print('🚀 Starting Halalo scraper...')
print(f'📋 Sheet: {sheet_name}')

product_links = get_all_product_links()
print(f'\n📦 Found {len(product_links)} unique products')

if not product_links:
    print('⚠️ No products found! Check category URLs or selectors.')
else:
    scraped_data = []
    for i, link in enumerate(product_links, 1):
        print(f'\n[{i}/{len(product_links)}] Scraping: {link}')
        data = scrape_product(link)
        if data:
            scraped_data.append(data)
        time.sleep(0.5)

    print(f'\n✅ Successfully scraped: {len(scraped_data)} products')
    print('📤 Updating Google Sheet...')

    sheet.clear()
    sheet.append_row(['Name', 'Price', 'Weight', 'Description', 'Image URL', 'Product URL'])

    if scraped_data:
        sheet.append_rows(scraped_data)
        print(f'✅ Done! {len(scraped_data)} products saved to "{sheet_name}"')
    else:
        print('⚠️ No data to save!')
