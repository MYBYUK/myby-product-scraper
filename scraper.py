import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

URL = "https://halalo.co.uk/index.php?dispatch=companies.view&company_id=3&scroller_id=category_1126"
SHEET_NAME = os.environ['SHEET_NAME']

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("Starting scrape from Halalo...")

response = requests.get(URL, headers=headers, timeout=30)
soup = BeautifulSoup(response.content, 'html.parser')

products = []
items = soup.select('.ty-grid-list__item')

print(f"Found {len(items)} products on page")

for item in items:
    try:
        name_elem = item.select_one('.ty-grid-list__item-name')
        if not name_elem:
            continue
        name = name_elem.text.strip()
        
        price_elem = item.select_one('.ty-price-num')
        price = price_elem.text.strip() if price_elem else '0.00'
        
        link_elem = item.select_one('a.ty-grid-list__image')
        link = link_elem['href'] if link_elem else ''
        if link and not link.startswith('http'):
            link = 'https://halalo.co.uk' + link
        
        img_elem = item.select_one('img.ty-pict')
        img_url = img_elem.get('data-src', img_elem.get('src', '')) if img_elem else ''
        if img_url and not img_url.startswith('http'):
            img_url = 'https://halalo.co.uk' + img_url
        
        category = 'other'
        emoji = '📦'
        name_lower = name.lower()
        
        if any(word in name_lower for word in ['lamb', 'mutton', 'beef', 'goat', 'لحم', 'خروف', 'بقر']):
            category = 'meat'
            emoji = '🥩'
        elif any(word in name_lower for word in ['chicken', 'دجاج']):
            category = 'meat'
            emoji = '🍗'
        elif any(word in name_lower for word in ['rice', 'basmati', 'أرز', 'رز']):
            category = 'rice'
            emoji = '🍚'
        elif any(word in name_lower for word in ['oil', 'زيت']):
            category = 'oil'
            emoji = '🫒'
        elif any(word in name_lower for word in ['honey', 'عسل']):
            category = 'sweets'
            emoji = '🍯'
        elif any(word in name_lower for word in ['dates', 'تمر']):
            category = 'sweets'
            emoji = '🌴'
        elif any(word in name_lower for word in ['spice', 'بهار', 'زعتر']):
            category = 'spices'
            emoji = '🧂'
        elif any(word in name_lower for word in ['lentil', 'عدس', 'bean', 'فول']):
            category = 'rice'
            emoji = '🫘'
            
        products.append([
            name,
            category,
            f'£{price}',
            emoji,
            f'بدي أطلب {name}',
            img_url,
            link
        ])
        
        print(f"Scraped: {name}")
        time.sleep(0.3)
        
    except Exception as e:
        print(f"Error scraping item: {e}")
        continue

print(f"\nTotal products scraped: {len(products)}")

# الاتصال بـ Google Sheets - بجيب الكريدينشالز من الـ Secrets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ['GDRIVE_CREDS'])  # هذا بقرأه من GitHub Secrets
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open(SHEET_NAME).sheet1
sheet.clear()
sheet.append_row(['name', 'category', 'price', 'emoji', 'whatsapp_text', 'image_url', 'product_url'])

for p in products:
    sheet.append_row(p)

print(f"✅ Done! Updated Google Sheet with {len(products)} products")
