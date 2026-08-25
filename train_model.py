import pandas as pd
import numpy as np
import yfinance as yf
import os
from datetime import datetime
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# تنظیمات کلی
# ==========================================
CRYPTO_NEWS_FILE = "crypto_news_dataset.csv"
IRAN_NEWS_FILE = "iran_market_news_dataset.csv"
REPORT_FILE = "model_performance_report.csv"

def load_news_data(file_path):
    """بارگذاری و پردازش داده‌های خبری"""
    if not os.path.exists(file_path):
        print(f"⚠️ فایل {file_path} یافت نشد.")
        return None
    
    df = pd.read_csv(file_path)
    print(f"✓ بارگذاری {len(df)} خبر از {file_path}")
    
    # گروه‌بندی بر اساس تاریخ و محاسبه میانگین احساسات روزانه
    daily_sentiment = df.groupby('date').agg({
        'sentiment_score': 'mean',
        'title': 'count'
    }).rename(columns={'title': 'news_count'})
    
    daily_sentiment.index = pd.to_datetime(daily_sentiment.index)
    
    # میانگین متحرک ۳ روزه (برای فیلتر نویز)
    daily_sentiment['Sentiment_SMA_3'] = daily_sentiment['sentiment_score'].rolling(window=3).mean()
    
    # جلوگیری از Look-Ahead Bias (یک روز شیفت)
    daily_sentiment = daily_sentiment.shift(1)
    
    return daily_sentiment

def get_market_data(ticker, period="3y"):
    """دریافت داده‌های قیمت از yfinance"""
    print(f"✓ دریافت داده‌های قیمت برای {ticker}...")
    data = yf.Ticker(ticker).history(period=period)
    data.index = data.index.tz_localize(None)
    return data

def build_features(market_data, sentiment_data):
    """ساخت ویژگی‌های مدل"""
    # ادغام داده‌های قیمت و احساسات
    data = market_data.join(sentiment_data, how='left')
    
    # پر کردن مقادیر خالی
    data['sentiment_score'] = data['sentiment_score'].fillna(0)
    data['news_count'] = data['news_count'].fillna(0)
    data['Sentiment_SMA_3'] = data['Sentiment_SMA_3'].fillna(0)
    
    # مهندسی ویژگی‌های تکنیکال
    data['SMA_20'] = data['Close'].rolling(window=20).mean()
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['Dist_from_SMA50'] = (data['Close'] - data['SMA_50']) / data['SMA_50']
    
    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    data['Volume_Change'] = data['Volume'].pct_change()
    data['Daily_Return'] = data['Close'].pct_change()
    
    # احساسات ترکیبی (اگر خبری نبود، از بازده دیروز استفاده کن)
    data['Hybrid_Sentiment'] = np.where(
        data['news_count'] > 0,
        data['sentiment_score'],
        np.where(data['Daily_Return'].shift(1) < -0.02, -1.0,
                 np.where(data['Daily_Return'].shift(1) > 0.02, 1.0, 0.0))
    )
    data['Hybrid_Sentiment_SMA_3'] = data['Hybrid_Sentiment'].rolling(window=3).mean()
    
    # شیفت برای جلوگیری از Look-Ahead
    data['Hybrid_Sentiment'] = data['Hybrid_Sentiment'].shift(1)
    data['Hybrid_Sentiment_SMA_3'] = data['Hybrid_Sentiment_SMA_3'].shift(1)
    
    data.dropna(inplace=True)
    
    return data

def train_and_evaluate(data, market_name):
    """آموزش و ارزیابی مدل"""
    print(f"\n{'='*60}")
    print(f"آموزش مدل برای {market_name}")
    print(f"{'='*60}")
    
    # تعریف هدف: آیا ۳ روز دیگر قیمت ۰.۵٪ بالاتر است؟
    data['Target'] = (data['Close'].shift(-3) > data['Close'] * 1.005).astype(int)
    
    features = [
        'SMA_20', 'Dist_from_SMA50', 'RSI', 'Volume_Change',
        'Hybrid_Sentiment', 'Hybrid_Sentiment_SMA_3'
    ]
    
    X = data[features]
    y = data['Target']
    
    # تقسیم داده‌ها (۸۰٪ آموزش، ۲۰٪ تست)
    split_idx = int(len(data) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    # آموزش مدل
    model = HistGradientBoostingClassifier(class_weight='balanced', random_state=42)
    model.fit(X_train, y_train)
    
    # ارزیابی
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    
    print(f"\nدقت مدل: {accuracy * 100:.2f}%")
    print("\nگزارش دقیق‌تر:")
    print(classification_report(y_test, predictions, target_names=['نزول (0)', 'صعود (1)']))
    
    # پیش‌بینی امروز
    last_row = X.iloc[[-1]]
    today_pred = model.predict(last_row)[0]
    pred_label = "صعودی 🟢" if today_pred == 1 else "نزولی 🔴"
    
    print(f"\n🔮 پیش‌بینی مدل برای فردا: {pred_label}")
    
    # بک‌تست ساده
    X_test_copy = X_test.copy()
    X_test_copy['Prediction'] = predictions
    X_test_copy['Actual'] = y_test
    
    INITIAL_CAPITAL = 10000
    RISK = 0.01
    REWARD = 0.025
    
    capital = INITIAL_CAPITAL
    wins = 0
    losses = 0
    
    for _, row in X_test_copy.iterrows():
        if row['Prediction'] == 1:
            if row['Actual'] == 1:
                capital += capital * REWARD
                wins += 1
            else:
                capital -= capital * RISK
                losses += 1
    
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    profit_pct = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    print(f"\n{'='*60}")
    print(f"نتایج بک‌تست:")
    print(f"  سرمایه اولیه: {INITIAL_CAPITAL:,}$")
    print(f"  سرمایه نهایی: {capital:,.2f}$")
    print(f"  سود/ضرر: {profit_pct:.2f}%")
    print(f"  تعداد ترید: {total_trades}")
    print(f"  نرخ برد: {win_rate:.2f}%")
    print(f"{'='*60}\n")
    
    return {
        'market': market_name,
        'date': datetime.now().strftime("%Y-%m-%d"),
        'accuracy': round(accuracy * 100, 2),
        'total_trades': total_trades,
        'win_rate': round(win_rate, 2),
        'profit_pct': round(profit_pct, 2),
        'prediction': pred_label
    }

def main():
    print(f"\n{'='*60}")
    print(f"سیستم آموزش مدل هوش مصنوعی - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")
    
    results = []
    
    # ==========================================
    # ۱. مدل کریپتو (بیت‌کوین + اخبار کریپتو)
    # ==========================================
    print("\n📊 بخش ۱: بازار کریپتو (BTC-USD)")
    crypto_news = load_news_data(CRYPTO_NEWS_FILE)
    
    if crypto_news is not None and len(crypto_news) > 30:
        btc_data = get_market_data("BTC-USD")
        btc_features = build_features(btc_data, crypto_news)
        
        if len(btc_features) > 100:
            result = train_and_evaluate(btc_features, "Bitcoin")
            results.append(result)
        else:
            print("⚠️ داده‌های کافی برای بیت‌کوین وجود ندارد.")
    else:
        print("⚠️ دیتاست اخبار کریپتو خالی یا خیلی کوچک است.")
    
    # ==========================================
    # ۲. مدل طلا (انس جهانی + اخبار ایران)
    # ==========================================
    print("\n📊 بخش ۲: بازار طلا (GC=F به عنوان نماینده طلای ایران)")
    iran_news = load_news_data(IRAN_NEWS_FILE)
    
    if iran_news is not None and len(iran_news) > 30:
        gold_data = get_market_data("GC=F")
        gold_features = build_features(gold_data, iran_news)
        
        if len(gold_features) > 100:
            result = train_and_evaluate(gold_features, "Gold")
            results.append(result)
        else:
            print("⚠️ داده‌های کافی برای طلا وجود ندارد.")
    else:
        print("⚠️ دیتاست اخبار ایران خالی یا خیلی کوچک است.")
    
    # ==========================================
    # ۳. ذخیره گزارش در فایل CSV
    # ==========================================
    if results:
        results_df = pd.DataFrame(results)
        
        # ادغام با گزارش‌های قبلی (اگر وجود دارد)
        if os.path.exists(REPORT_FILE):
            existing_df = pd.read_csv(REPORT_FILE)
            combined_df = pd.concat([existing_df, results_df], ignore_index=True)
        else:
            combined_df = results_df
        
        combined_df.to_csv(REPORT_FILE, index=False, encoding='utf-8')
        
        print(f"\n✅ گزارش عملکرد در {REPORT_FILE} ذخیره شد.")
        print(f"📈 تعداد کل روزهای ثبت شده: {len(combined_df)}")
    else:
        print("\n⚠️ هیچ مدلی آموزش داده نشد. دیتاست‌ها هنوز کوچک هستند.")
    
    print(f"\n{'='*60}")
    print("پایان فرآیند آموزش مدل")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
