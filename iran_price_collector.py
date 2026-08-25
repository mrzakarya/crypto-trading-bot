import requests
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import time

DATASET_FILE = "iran_market_prices.csv"

def get_tgju_price():
    """تلاش برای دریافت قیمت دلار و طلا از TGJU"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    dollar_price = None
    gold_price = None
    
    try:
        # دریافت صفحه اصلی TGJU
        response = requests.get("https://www.tgju.org/", headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # استخراج قیمت دلار (معمولاً در data-col="price" قرار دارد)
        # توجه: کلاس‌ها ممکن است تغییر کنند، این یک روش عمومی است
        dollar_elem = soup.find('a', {'href': '/profile/price_dollar_rl'})
        if dollar_elem:
            price_text = dollar_elem.find('span', {'data-col': 'price'}).text.replace(',', '')
            dollar_price = float(price_text)
            
        # استخراج قیمت طلای ۱۸ عیار
        gold_elem = soup.find('a', {'href': '/profile/geram18'})
        if gold_elem:
            price_text = gold_elem.find('span', {'data-col': 'price'}).text.replace(',', '')
            gold_price = float(price_text)
            
    except Exception as e:
        print(f"  ⚠️ دریافت از TGJU ناموفق بود (محدودیت IP یا تغییر ساختار): {e}")
        
    return dollar_price, gold_price

def get_global_prices():
    """دریافت قیمت انس جهانی طلا (که محرک اصلی طلای ایران است)"""
    try:
        # GC=F نماد طلای جهانی در یاهو فایننس است
        gold_global = yf.Ticker("GC=F").history(period="1d")
        if not gold_global.empty:
            return float(gold_global['Close'].iloc[-1])
    except:
        pass
    return None

def collect_daily_prices():
    print(f"\n{'='*60}")
    print(f"شروع جمع‌آوری قیمت‌ها - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # ۱. دریافت قیمت‌های داخلی
    print("در حال دریافت قیمت دلار و طلا از TGJU...")
    dollar_price, gold_price = get_tgju_price()
    
    # ۲. دریافت قیمت جهانی
    print("در حال دریافت قیمت انس جهانی طلا...")
    global_gold = get_global_prices()
    
    # ۳. ساخت دیتافریم جدید
    new_data = {
        'date': [today_str],
        'dollar_price': [dollar_price],
        'gold_18k_price': [gold_price],
        'global_gold_price': [global_gold]
    }
    new_df = pd.DataFrame(new_data)
    
    print(f"  ✓ دلار: {dollar_price if dollar_price else 'نامشخص'}")
    print(f"  ✓ طلای ۱۸ عیار: {gold_price if gold_price else 'نامشخص'}")
    print(f"  ✓ انس جهانی: {global_gold if global_gold else 'نامشخص'}")
    
    # ۴. ادغام با دیتاست قبلی
    if os.path.exists(DATASET_FILE):
        existing_df = pd.read_csv(DATASET_FILE)
        
        # جلوگیری از ثبت تکراری برای یک روز
        existing_df = existing_df[existing_df['date'] != today_str]
        
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
    
    # مرتب‌سازی بر اساس تاریخ
    combined_df = combined_df.sort_values('date', ascending=False)
    combined_df.to_csv(DATASET_FILE, index=False, encoding='utf-8')
    
    print(f"\n✅ دیتاست قیمت‌ها ذخیره شد. تعداد کل روزها: {len(combined_df)}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    collect_daily_prices()
