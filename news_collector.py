import feedparser
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta
import os
import time
import re

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed"
]

DATASET_FILE = "crypto_news_dataset.csv"

def normalize_title(title):
    """
    نرمال‌سازی تیتر برای تشخیص بهتر تکراری‌ها
    - تبدیل به حروف کوچک
    - حذف کاراکترهای اضافی
    - حذف فاصله‌های اضافی
    """
    title = title.lower().strip()
    title = re.sub(r'[^\w\s]', '', title)  # حذف علائم نگارشی
    title = re.sub(r'\s+', ' ', title)     # حذف فاصله‌های اضافی
    return title

def clean_url(url):
    """
    پاکسازی URL برای حذف پارامترهای tracking
    مثال: example.com/article?utm_source=twitter -> example.com/article
    """
    if '?' in url:
        url = url.split('?')[0]
    return url

def collect_daily_news():
    print(f"\n{'='*60}")
    print(f"شروع جمع‌آوری اخبار - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    analyzer = SentimentIntensityAnalyzer()
    all_news = []
    
    # تاریخ ۷ روز پیش (برای جلوگیری از جمع‌آوری اخبار خیلی قدیمی)
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for feed_url in RSS_FEEDS:
        print(f"در حال دریافت اخبار از: {feed_url}")
        
        try:
            feed = feedparser.parse(feed_url)
            news_count_before = len(all_news)
            
            for entry in feed.entries:
                title = entry.get('title', '').strip()
                link = entry.get('link', '').strip()
                published = entry.get('published', '')
                
                if not title or not link:
                    continue
                
                # استخراج و اعتبارسنجی تاریخ
                try:
                    pub_date = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %z")
                    
                    # ❌ رد کردن اخبار قدیمی‌تر از ۷ روز
                    if pub_date < cutoff_date:
                        continue
                    
                    date_str = pub_date.strftime("%Y-%m-%d")
                except:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                
                # پاکسازی URL
                link = clean_url(link)
                
                # تحلیل احساسات
                sentiment_score = analyzer.polarity_scores(title)['compound']
                
                # نرمال‌سازی تیتر برای تشخیص تکراری‌ها
                normalized_title = normalize_title(title)
                
                all_news.append({
                    'date': date_str,
                    'title': title,
                    'normalized_title': normalized_title,  # برای حذف تکراری
                    'link': link,
                    'source': feed_url,
                    'sentiment_score': sentiment_score
                })
            
            print(f"  ✓ {len(all_news) - news_count_before} خبر از این منبع")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ✗ خطا در {feed_url}: {e}")
            continue
    
    if not all_news:
        print("❌ هیچ خبری دریافت نشد.")
        return
    
    new_df = pd.DataFrame(all_news)
    
    # ==========================================
    # 🛡️ لایه‌های محافظتی در برابر تکراری‌ها
    # ==========================================
    
    # لایه ۱: حذف تکراری در همین اجرای فعلی (بر اساس لینک)
    new_df = new_df.drop_duplicates(subset=['link'], keep='first')
    print(f"\n📊 پس از حذف تکراری‌های داخلی: {len(new_df)} خبر")
    
    # لایه ۲: حذف تکراری بر اساس تیتر نرمال‌شده (یک خبر در چند منبع)
    new_df = new_df.drop_duplicates(subset=['normalized_title'], keep='first')
    print(f"📊 پس از حذف تکراری‌های تیتر یکسان: {len(new_df)} خبر")
    
    # لایه ۳: ادغام با دیتاست قبلی و حذف تکراری‌های تاریخی
    if os.path.exists(DATASET_FILE):
        print(f"\n📂 دیتاست قبلی یافت شد: {DATASET_FILE}")
        existing_df = pd.read_csv(DATASET_FILE)
        print(f"   تعداد اخبار قبلی: {len(existing_df)}")
        
        # ستون normalized_title در دیتاست قبلی ممکن است نباشد
        if 'normalized_title' not in existing_df.columns:
            existing_df['normalized_title'] = existing_df['title'].apply(normalize_title)
        
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        # حذف تکراری بر اساس لینک (اولویت با نسخه جدیدتر)
        combined_df = combined_df.drop_duplicates(subset=['link'], keep='last')
        
        # حذف تکراری بر اساس تیتر نرمال‌شده (اولویت با نسخه جدیدتر)
        combined_df = combined_df.drop_duplicates(subset=['normalized_title'], keep='last')
        
        new_count = len(combined_df) - len(existing_df)
        print(f"✅ تعداد اخبار جدید اضافه شده: {new_count}")
        print(f"✅ تعداد کل اخبار پس از حذف تکراری: {len(combined_df)}")
    else:
        print("\n🆕 دیتاست جدید در حال ساخت...")
        combined_df = new_df
    
    # مرتب‌سازی بر اساس تاریخ (جدیدترین اول)
    combined_df = combined_df.sort_values('date', ascending=False)
    
    # حذف ستون کمکی (دیگر نیازی نیست در فایل نهایی باشد)
    if 'normalized_title' in combined_df.columns:
        combined_df = combined_df.drop(columns=['normalized_title'])
    
    # ذخیره در فایل CSV
    combined_df.to_csv(DATASET_FILE, index=False, encoding='utf-8')
    
    print(f"\n{'='*60}")
    print(f"✅ دیتاست با موفقیت ذخیره شد")
    print(f"📊 تعداد کل اخبار در دیتاست: {len(combined_df)}")
    print(f"📅 بازه زمانی: {combined_df['date'].min()} تا {combined_df['date'].max()}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    collect_daily_news()
