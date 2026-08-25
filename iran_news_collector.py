import feedparser
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import re
from hazm import Normalizer, word_tokenize

# ==========================================
# تنظیمات مخصوص بازار ایران
# ==========================================

# منابع خبری فارسی (RSS) - به‌روزرسانی شده با لینک‌های پایدارتر
RSS_FEEDS_IRAN = [
    "https://tejaratnews.com/feed",               # تجارت نیوز (که قبلاً کار کرد)
    "https://donya-e-eqtesad.com/rss",            # دنیای اقتصاد (بسیار معتبر و پایدار)
    "https://www.eghtesadonline.com/fa/rss",      # اقتصاد آنلاین
    "https://www.bourse24.ir/rss",                # بورس ۲۴ (مخصوص بازار سرمایه)
    "https://www.asreeghtesad.com/fa/rss",        # عصر اقتصاد
    "https://www.tgju.org/profile/price_dollar_rl/rss" # RSS اختصاصی قیمت دلار از TGJU (اگر فعال باشد)
]

DATASET_FILE = "iran_market_news_dataset.csv"

# ==========================================
# 🧠 دیکشنری احساسات فارسی (ساخته شده بر اساس کلمات پرکاربرد اقتصادی)
# ==========================================

POSITIVE_WORDS = {
    'رشد', 'صعود', 'افزایش', 'سود', 'موفقیت', 'بهبود', 'جهش', 'رکورد',
    'سودده', 'مثبت', 'تقویت', 'بالا', 'پیشرفت', 'رونق', 'ثبات', 'تعادل',
    'کاهش_تورم', 'حمایت', 'توصیه', 'فرصت', 'جذب', 'سرمایه_گذاری',
    'بازگشت', 'جهش_تولید', 'صادرات', 'توسعه', 'اشتغال'
}

NEGATIVE_WORDS = {
    'ریزش', 'سقوط', 'کاهش', 'ضرر', 'شکست', 'بحران', 'تورم', 'رکود',
    'زیان', 'منفی', 'ضعف', 'پایین', 'افت', 'فشار', 'نوسان', 'بی_ثباتی',
    'تحریم', 'گرانی', 'بیکاری', 'ورشکستگی', 'خروج', 'انسداد', 'جریمه',
    'فساد', 'کمبود', 'اعتراض', 'توقف', 'اختلاف'
}

# راه‌اندازی نرمال‌ساز فارسی
normalizer = Normalizer()

def analyze_persian_sentiment(text):
    """
    تحلیل احساسات متن فارسی بر اساس دیکشنری کلمات
    خروجی: عددی بین -1 (کاملاً منفی) تا +1 (کاملاً مثبت)
    """
    if not text:
        return 0.0
    
    # نرمال‌سازی متن (یکسان‌سازی ی/ک، حذف اعراب، ...)
    text = normalizer.normalize(text)
    
    # توکنایز (جداسازی کلمات)
    try:
        tokens = word_tokenize(text)
    except:
        tokens = text.split()
    
    positive_count = 0
    negative_count = 0
    
    for token in tokens:
        token = token.strip()
        if token in POSITIVE_WORDS:
            positive_count += 1
        elif token in NEGATIVE_WORDS:
            negative_count += 1
    
    total = positive_count + negative_count
    if total == 0:
        return 0.0  # خنثی
    
    # نرمال‌سازی به بازه [-1, +1]
    score = (positive_count - negative_count) / total
    return round(score, 3)

# ==========================================
# توابع کمکی
# ==========================================

def normalize_title(title):
    title = normalizer.normalize(title).lower().strip()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title

def clean_url(url):
    if '?' in url:
        url = url.split('?')[0]
    return url

# ==========================================
# تابع اصلی جمع‌آوری
# ==========================================

def collect_daily_news():
    print(f"\n{'='*60}")
    print(f"شروع جمع‌آوری اخبار بازار ایران - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    all_news = []
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for feed_url in RSS_FEEDS_IRAN:
        print(f"در حال دریافت: {feed_url}")
        
        try:
            feed = feedparser.parse(feed_url)
            news_count_before = len(all_news)
            
            for entry in feed.entries:
                title = entry.get('title', '').strip()
                link = entry.get('link', '').strip()
                published = entry.get('published', '') or entry.get('updated', '')
                
                if not title or not link:
                    continue
                
                # استخراج تاریخ
                try:
                    # فرمت‌های رایج در RSS فارسی
                    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            pub_date = datetime.strptime(published, fmt)
                            break
                        except:
                            continue
                    else:
                        pub_date = datetime.now()
                    
                    if pub_date < cutoff_date:
                        continue
                    
                    date_str = pub_date.strftime("%Y-%m-%d")
                except:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                
                link = clean_url(link)
                
                # 🔥 تحلیل احساسات فارسی
                sentiment_score = analyze_persian_sentiment(title)
                
                normalized_title = normalize_title(title)
                
                all_news.append({
                    'date': date_str,
                    'title': title,
                    'normalized_title': normalized_title,
                    'link': link,
                    'source': feed_url,
                    'sentiment_score': sentiment_score
                })
            
            print(f"  ✓ {len(all_news) - news_count_before} خبر")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ✗ خطا: {e}")
            continue
    
    if not all_news:
        print("❌ هیچ خبری دریافت نشد.")
        return
    
    new_df = pd.DataFrame(all_news)
    
    # حذف تکراری‌ها
    new_df = new_df.drop_duplicates(subset=['link'], keep='first')
    new_df = new_df.drop_duplicates(subset=['normalized_title'], keep='first')
    print(f"\n📊 پس از حذف تکراری‌ها: {len(new_df)} خبر")
    
    # ادغام با دیتاست قبلی
    if os.path.exists(DATASET_FILE):
        existing_df = pd.read_csv(DATASET_FILE)
        if 'normalized_title' not in existing_df.columns:
            existing_df['normalized_title'] = existing_df['title'].apply(normalize_title)
        
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['link'], keep='last')
        combined_df = combined_df.drop_duplicates(subset=['normalized_title'], keep='last')
        
        new_count = len(combined_df) - len(existing_df)
        print(f"✅ اخبار جدید اضافه شده: {new_count}")
    else:
        combined_df = new_df
    
    combined_df = combined_df.sort_values('date', ascending=False)
    
    if 'normalized_title' in combined_df.columns:
        combined_df = combined_df.drop(columns=['normalized_title'])
    
    combined_df.to_csv(DATASET_FILE, index=False, encoding='utf-8')
    
    print(f"\n✅ دیتاست ذخیره شد. تعداد کل: {len(combined_df)}")
    print(f"📅 بازه: {combined_df['date'].min()} تا {combined_df['date'].max()}")

if __name__ == "__main__":
    collect_daily_news()
