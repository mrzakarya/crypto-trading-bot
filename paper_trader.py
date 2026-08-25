import pandas as pd
import numpy as np
import yfinance as yf
import joblib
import os
from datetime import datetime, timedelta

# ==========================================
# تنظیمات
# ==========================================
MODEL_FILE = "btc_trading_model.pkl"
LOG_FILE = "paper_trading_log.csv"
RISK_PER_TRADE = 0.01      # ۱٪ حد ضرر
REWARD_PER_TRADE = 0.025   # ۲.۵٪ حد سود

def load_model():
    """بارگذاری مدل آموزش‌دیده"""
    if not os.path.exists(MODEL_FILE):
        print(f"⚠️ فایل مدل '{MODEL_FILE}' یافت نشد.")
        print("   ابتدا باید مدل را آموزش دهید (dry_run_local.py) و در گیت‌هاب آپلود کنید.")
        return None
    try:
        model = joblib.load(MODEL_FILE)
        print(f"✓ مدل با موفقیت از '{MODEL_FILE}' بارگذاری شد.")
        return model
    except Exception as e:
        print(f"❌ خطا در بارگذاری مدل: {e}")
        return None

def build_features_for_today():
    """دریافت داده‌های اخیر و ساخت ویژگی‌ها دقیقاً مطابق زمان آموزش"""
    print("📊 در حال دریافت داده‌های قیمت بیت‌کوین (۶۰ روز اخیر)...")
    df = yf.Ticker("BTC-USD").history(period="60d")
    
    if df.empty or len(df) < 55:
        print("❌ داده‌های کافی از yfinance دریافت نشد.")
        return None, None
    
    df.index = df.index.tz_localize(None)
    
    # تولید احساسات شبیه‌سازی‌شده (چون دیتاست خبری هنوز کوچک است)
    np.random.seed(int(datetime.now().strftime("%Y%m%d")))
    df['Daily_Return'] = df['Close'].pct_change()
    base_sentiment = np.sign(df['Daily_Return'].shift(1)) * 0.4
    noise = np.random.normal(0, 0.3, len(df))
    df['sentiment_score'] = (base_sentiment + noise).clip(-1, 1)
    df['news_count'] = np.random.randint(5, 30, len(df))
    
    # مهندسی ویژگی‌ها (دقیقاً مطابق dry_run_local.py)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['Dist_from_SMA50'] = (df['Close'] - df['SMA_50']) / df['SMA_50']
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['Volume_Change'] = df['Volume'].pct_change()
    
    df['Hybrid_Sentiment'] = np.where(
        df['news_count'] > 0,
        df['sentiment_score'],
        np.where(df['Daily_Return'].shift(1) < -0.02, -1.0,
                 np.where(df['Daily_Return'].shift(1) > 0.02, 1.0, 0.0))
    )
    df['Hybrid_Sentiment_SMA_3'] = df['Hybrid_Sentiment'].rolling(window=3).mean()
    
    df['Hybrid_Sentiment'] = df['Hybrid_Sentiment'].shift(1)
    df['Hybrid_Sentiment_SMA_3'] = df['Hybrid_Sentiment_SMA_3'].shift(1)
    
    df.dropna(inplace=True)
    
    if df.empty:
        return None, None
    
    latest_row = df.iloc[-1]
    latest_price = latest_row['Close']
    
    features = ['SMA_20', 'Dist_from_SMA50', 'RSI', 'Volume_Change', 
                'Hybrid_Sentiment', 'Hybrid_Sentiment_SMA_3']
    
    X_today = latest_row[features].values.reshape(1, -1)
    
    return X_today, latest_row

def check_yesterday_prediction():
    """بررسی نتیجه پیش‌بینی دیروز"""
    if not os.path.exists(LOG_FILE):
        print("ℹ️ فایل لاگ هنوز وجود ندارد (اولین اجرا).")
        return
    
    df = pd.read_csv(LOG_FILE)
    if df.empty:
        return
    
    # پیدا کردن آخرین پیش‌بینی در وضعیت "pending"
    pending_rows = df[df['result'] == 'pending']
    if pending_rows.empty:
        print("ℹ️ هیچ پیش‌بینی در انتظار بررسی وجود ندارد.")
        return
    
    last_pending_idx = pending_rows.index[-1]
    last_pending = df.loc[last_pending_idx]
    entry_date = pd.to_datetime(last_pending['date'])
    entry_price = float(last_pending['entry_price'])
    prediction = last_pending['prediction']
    
    # دریافت قیمت امروز
    try:
        today_data = yf.Ticker("BTC-USD").history(period="5d")
        if len(today_data) < 2:
            print("⚠️ داده کافی برای بررسی پیش‌بینی دیروز وجود ندارد.")
            return
        
        today_close = float(today_data['Close'].iloc[-1])
        today_date = today_data.index[-1].strftime("%Y-%m-%d")
        
        # بررسی بر اساس تعریف Target مدل (۰.۵٪ رشد در ۳ روز)
        # اما برای سادگی، فقط تغییر از دیروز تا امروز را چک می‌کنیم
        price_change_pct = ((today_close - entry_price) / entry_price) * 100
        
        # تعیین نتیجه
        if prediction == 'UP':
            if price_change_pct >= 0.5:
                result = 'win'
            else:
                result = 'loss'
        else:  # DOWN
            if price_change_pct <= -0.5:
                result = 'win'
            else:
                result = 'loss'
        
        # به‌روزرسانی فایل لاگ
        df.loc[last_pending_idx, 'result'] = result
        df.loc[last_pending_idx, 'exit_price'] = today_close
        df.loc[last_pending_idx, 'exit_date'] = today_date
        df.loc[last_pending_idx, 'price_change_pct'] = round(price_change_pct, 2)
        
        df.to_csv(LOG_FILE, index=False)
        
        emoji = '✅' if result == 'win' else '❌'
        print(f"\n{emoji} نتیجه پیش‌بینی دیروز بررسی شد:")
        print(f"   تاریخ ورود: {entry_date.strftime('%Y-%m-%d')} | قیمت ورود: {entry_price:,.2f}$")
        print(f"   تاریخ خروج: {today_date} | قیمت خروج: {today_close:,.2f}$")
        print(f"   تغییر قیمت: {price_change_pct:+.2f}%")
        print(f"   نتیجه: {'سود (Win)' if result == 'win' else 'ضرر (Loss)'}")
        
    except Exception as e:
        print(f"⚠️ خطا در بررسی پیش‌بینی دیروز: {e}")

def make_today_prediction():
    """پیش‌بینی امروز و ثبت در لاگ"""
    print("\n" + "="*70)
    print("🔮 پیش‌بینی امروز")
    print("="*70)
    
    model = load_model()
    if model is None:
        return
    
    X_today, latest_row = build_features_for_today()
    if X_today is None:
        return
    
    # پیش‌بینی مدل
    prediction = model.predict(X_today)[0]
    pred_label = 'UP' if prediction == 1 else 'DOWN'
    
    # دریافت احتمال (Probability) از مدل
    try:
        probabilities = model.predict_proba(X_today)[0]
        confidence = max(probabilities) * 100
    except:
        confidence = 50.0
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    price = float(latest_row['Close'])
    rsi = float(latest_row['RSI'])
    sentiment = float(latest_row['Hybrid_Sentiment'])
    
    # ثبت در لاگ
    new_entry = pd.DataFrame([{
        'date': today_str,
        'entry_price': round(price, 2),
        'prediction': pred_label,
        'confidence': round(confidence, 2),
        'rsi': round(rsi, 2),
        'sentiment': round(sentiment, 3),
        'result': 'pending',
        'exit_price': None,
        'exit_date': None,
        'price_change_pct': None
    }])
    
    if os.path.exists(LOG_FILE):
        existing_df = pd.read_csv(LOG_FILE)
        # جلوگیری از ثبت تکراری برای یک روز
        existing_df = existing_df[existing_df['date'] != today_str]
        combined_df = pd.concat([existing_df, new_entry], ignore_index=True)
    else:
        combined_df = new_entry
    
    combined_df.to_csv(LOG_FILE, index=False)
    
    # نمایش نتیجه
    emoji = '🟢' if pred_label == 'UP' else '🔴'
    print(f"\n{emoji} پیش‌بینی مدل برای فردا: {'صعودی (UP)' if pred_label == 'UP' else 'نزولی (DOWN)'}")
    print(f"   💰 قیمت ورود: {price:,.2f} دلار")
    print(f"   🎯 اطمینان مدل: {confidence:.1f}%")
    print(f"   📊 RSI: {rsi:.2f}")
    print(f"   📰 احساسات بازار: {sentiment:.3f}")
    print(f"\n✅ پیش‌بینی در '{LOG_FILE}' ثبت شد.")

def show_summary():
    """نمایش خلاصه عملکرد کلی"""
    if not os.path.exists(LOG_FILE):
        return
    
    df = pd.read_csv(LOG_FILE)
    if df.empty:
        return
    
    completed = df[df['result'].isin(['win', 'loss'])]
    if completed.empty:
        print("\nℹ️ هنوز هیچ پیش‌بینی‌ای به نتیجه نرسیده است.")
        return
    
    wins = len(completed[completed['result'] == 'win'])
    losses = len(completed[completed['result'] == 'loss'])
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    # محاسبه سرمایه فرضی
    capital = 10000
    for _, row in completed.iterrows():
        if row['prediction'] == 'UP' and row['result'] == 'win':
            capital += capital * REWARD_PER_TRADE
        elif row['prediction'] == 'UP' and row['result'] == 'loss':
            capital -= capital * RISK_PER_TRADE
        elif row['prediction'] == 'DOWN' and row['result'] == 'win':
            capital += capital * REWARD_PER_TRADE
        elif row['prediction'] == 'DOWN' and row['result'] == 'loss':
            capital -= capital * RISK_PER_TRADE
    
    profit_pct = ((capital - 10000) / 10000) * 100
    
    print("\n" + "="*70)
    print("📊 خلاصه عملکرد Paper Trader")
    print("="*70)
    print(f"   کل پیش‌بینی‌ها: {total}")
    print(f"   ✅ بردها: {wins} | ❌ باخت‌ها: {losses}")
    print(f"   🎯 نرخ برد: {win_rate:.2f}%")
    print(f"   💵 سرمایه فرضی: ۱۰,۰۰۰$ → {capital:,.2f}$")
    print(f"   📈 سود/ضرر کل: {profit_pct:+.2f}%")
    print("="*70)

def main():
    print("\n" + "="*70)
    print(f"🤖 سیستم Paper Trading - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    # ۱. بررسی پیش‌بینی دیروز
    check_yesterday_prediction()
    
    # ۲. پیش‌بینی امروز
    make_today_prediction()
    
    # ۳. نمایش خلاصه
    show_summary()
    
    print("\n✅ فرآیند Paper Trading با موفقیت انجام شد.")

if __name__ == "__main__":
    main()
