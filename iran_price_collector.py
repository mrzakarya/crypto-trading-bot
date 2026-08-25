import requests
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

DATASET_FILE = "iran_market_prices.csv"

def get_tgju_price():
    """تلاش سریع برای دریافت قیمت دلار و طلا از TGJU"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    dollar_price = None
    gold_price = None
    
    try:
        print("  ⏳ در حال اتصال به TGJU (مهلت ۵ ثانیه)...")
        response = requests.get("https://www.tgju.org/", headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        dollar_elem = soup.find('a', {'href': '/profile/price_dollar_rl'})
        if dollar_elem:
            price_span = dollar_elem.find('span', {'data-col': 'price'})
            if price_span:
                dollar_price = float(price_span.text.replace(',', ''))
            
        gold_elem = soup.find('a', {'href': '/profile/geram18'})
        if gold_elem:
            price_span = gold_elem.find('span', {'data-col': 'price'})
            if price_span:
                gold_price = float(price_span.text.replace(',', ''))
                
    except requests.exceptions.Timeout:
        print("  ⚠️ خطا: زمان انتظار برای TGJU به پایان رسید.")
    except Exception as e:
        print(f"  ⚠️ خطا در دریافت از TGJU: {type(e).__name__}")
        
    return dollar_price, gold_price

def get_global_prices():
    """دریافت سریع قیمت انس جهانی طلا"""
    try:
        print("  ⏳ در حال دریافت قیمت انس جهانی...")
        ticker = yf.Ticker("GC=F")
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception as e:
        print(f"  ⚠️ خطا در دریافت قیمت جهانی: {type(e).__name__}")
    return None

def collect_daily_prices():
    print(f"\n{'='*60}")
    print(f"شروع جمع‌آوری قیمت‌ها - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # ۱. دریافت قیمت‌ها
    dollar_price, gold_price = get_tgju_price()
    global_gold = get_global_prices()
    
    # ==========================================
    # 🔥 منطق هوشمند: اگر داده اصلی (دلار) دریافت نشد، کلاً ذخیره نکن!
    # ==========================================
    if dollar_price is None:
        print("\n🚫 هشدار: قیمت دلار دریافت نشد.")
        print("✅ برای حفظ کیفیت دیتاست، امروز هیچ ردیفی ذخیره نمی‌شود.")
        print("فایل دیتاست دست‌نخورده و پاک باقی می‌ماند.")
        return  # خروج از تابع بدون ذخیره‌سازی
    
    # ۲. اگر به اینجا رسیدیم، یعنی حداقل قیمت دلار را داریم. ساخت دیتافریم
    new_data = {
        'date': [today_str],
        'dollar_price': [dollar_price],
        'gold_18k_price': [gold_price], # ممکن است None باشد که اشکالی ندارد
        'global_gold_price': [global_gold] # ممکن است None باشد که اشکالی ندارد
    }
    new_df = pd.DataFrame(new_data)
    
    print(f"\n📊 نتایج استخراج موفق:")
    print(f"  💵 دلار: {dollar_price} تومان")
    print(f"  🥇 طلای ۱۸ عیار: {gold_price if gold_price else 'نامشخص'}")
    print(f"  🌍 انس جهانی: {global_gold if global_gold else 'نامشخص'}")
    
    # ۳. ادغام با دیتاست قبلی
    if os.path.exists(DATASET_FILE):
        existing_df = pd.read_csv(DATASET_FILE)
        # جلوگیری از ثبت تکراری برای یک روز (اگر دستی چند بار ران شد)
        existing_df = existing_df[existing_df['date'] != today_str]
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
    
    combined_df = combined_df.sort_values('date', ascending=False)
    combined_df.to_csv(DATASET_FILE, index=False, encoding='utf-8')
    
    print(f"\n✅ دیتاست قیمت‌ها با موفقیت به‌روزرسانی شد.")
    print(f"📈 تعداد کل روزهای دارای داده: {len(combined_df)}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    collect_daily_prices()
