import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ==========================================
# تنظیمات اولیه و راست‌چین (RTL)
# ==========================================
st.set_page_config(page_title="داشبورد ربات تریدر هوشمند", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .stApp, .block-container, [data-testid="stVerticalBlock"] { direction: rtl !important; text-align: right !important; }
    [data-testid="stMetric"], [data-testid="stMetricLabel"], [data-testid="stMetricValue"] { direction: rtl !important; text-align: right !important; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; gap: 8px; }
    .dataframe { direction: rtl !important; }
    h1, h2, h3, h4, p, span, div { text-align: right !important; }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=30000, limit=None, key="dashboard_autorefresh")

st.title("🤖 داشبورد ربات تریدر هوشمند")
st.caption(f"⏰ آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

tab_prices, tab_robot, tab_votes, tab_data = st.tabs(["💹 قیمت‌های زنده", "🤖 عملکرد ربات", "🗳️ رأی‌گیری کمیته", "📡 وضعیت داده‌ها"])

# ==========================================
# تابع اسکرپینگ هوشمند از TGJU
# ==========================================
@st.cache_data(ttl=300)  # کش ۵ دقیقه‌ای برای جلوگیری از بن شدن IP
def get_iran_market_prices():
    """دریافت قیمت دلار و طلای ۱۸ عیار مستقیماً از tgju.org"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
    }
    
    dollar_price = None
    gold_price = None
    
    try:
        response = requests.get('https://www.tgju.org/', headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # استخراج قیمت دلار
        dollar_elem = soup.find('a', {'href': '/profile/price_dollar_rl'})
        if dollar_elem:
            price_span = dollar_elem.find('span', {'data-col': 'price'})
            if price_span:
                dollar_price = float(price_span.text.replace(',', ''))
                
        # استخراج قیمت طلای ۱۸ عیار
        gold_elem = soup.find('a', {'href': '/profile/geram18'})
        if gold_elem:
            price_span = gold_elem.find('span', {'data-col': 'price'})
            if price_span:
                gold_price = float(price_span.text.replace(',', ''))
                
        return dollar_price, gold_price
    except Exception as e:
        return None, None

# ==========================================
# تب ۱: قیمت‌های زنده بازار
# ==========================================
with tab_prices:
    st.subheader("💹 قیمت‌های زنده بازار")
    st.caption("⏱️ به‌روزرسانی خودکار هر ۵ دقیقه | دلار و طلا از TGJU، کریپتو از Yahoo Finance")
    
    # ۱. دریافت قیمت‌های ایران
    dollar_iran, gold_18k = get_iran_market_prices()
    
    # ۲. دریافت قیمت‌های جهانی و کریپتو
    crypto_prices = {}
    crypto_map = {'BTC-USD': 'BTC', 'ETH-USD': 'ETH', 'SOL-USD': 'SOL', 'BNB-USD': 'BNB', 'XRP-USD': 'XRP'}
    
    for ticker, name in crypto_map.items():
        try:
            data = yf.Ticker(ticker).history(period='2d')
            if len(data) >= 2:
                current = float(data['Close'].iloc[-1])
                previous = float(data['Close'].iloc[-2])
                change = ((current - previous) / previous) * 100
                crypto_prices[name] = {'price': current, 'change': change}
        except:
            pass

    # نمایش ارزهای دیجیتال
    st.markdown("#### 🪙 ارزهای دیجیتال")
    crypto_cols = st.columns(5)
    for i, (name, data) in enumerate(crypto_prices.items()):
        with crypto_cols[i]:
            delta_color = "normal" if data['change'] >= 0 else "inverse"
            st.metric(
                label=name,
                value=f"${data['price']:,.2f}",
                delta=f"{data['change']:+.2f}%",
                delta_color=delta_color
            )
            
    st.markdown("---")
    
    # نمایش طلا و دلار ایران
    st.markdown("#### 🇮🇷 بازار ایران (مستقیم از TGJU)")
    iran_cols = st.columns(2)
    
    with iran_cols[0]:
        if dollar_iran:
            # تخمین تغییرات بر اساس انس جهانی (چون TGJU تغییر لحظه‌ای در API عمومی ندارد)
            st.metric(
                label="💵 دلار بازار آزاد",
                value=f"{dollar_iran:,.0f} تومان",
                delta="بروزرسانی زنده",
                delta_color="off"
            )
        else:
            st.metric(label="💵 دلار بازار آزاد", value="—", delta="خطا در دریافت از TGJU")
            st.caption("⚠️ ممکن است IP سرور استریم‌لیت موقتاً توسط TGJU محدود شده باشد.")

    with iran_cols[1]:
        if gold_18k:
            st.metric(
                label="💰 طلای ۱۸ عیار (هر گرم)",
                value=f"{gold_18k:,.0f} تومان",
                delta="بروزرسانی زنده",
                delta_color="off"
            )
        else:
            st.metric(label="💰 طلای ۱۸ عیار", value="—", delta="خطا در دریافت از TGJU")

# ==========================================
# تب ۲: عملکرد ربات
# ==========================================
with tab_robot:
    st.subheader("🤖 عملکرد Paper Trading")
    @st.cache_data(ttl=3600)
    def load_robot_data():
        try:
            url = "https://raw.githubusercontent.com/mrzakarya/crypto-trading-bot/main/paper_trading_log.csv"
            return pd.read_csv(url)
        except:
            return pd.DataFrame()
    
    df = load_robot_data()
    if not df.empty:
        completed = df[df['result'].isin(['win', 'loss'])]
        total = len(completed)
        wins = len(completed[completed['result'] == 'win'])
        win_rate = (wins / total * 100) if total > 0 else 0
        
        capital = 10000
        for _, row in completed.iterrows():
            capital += capital * 0.025 if row['result'] == 'win' else -capital * 0.01
            
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 سرمایه فعلی", f"{capital:,.0f} $", f"{((capital-10000)/10000)*100:+.2f}%")
        col2.metric("📊 تعداد تریدها", total)
        col3.metric("🎯 نرخ برد", f"{win_rate:.1f}%")
        
        st.markdown("---")
        display_df = df[['date', 'prediction', 'confidence', 'entry_price', 'result']].copy()
        display_df['prediction'] = display_df['prediction'].apply(lambda x: '🟢 صعودی' if x == 'UP' else '🔴 نزولی')
        st.dataframe(display_df.style.format({'entry_price': '{:,.2f} $', 'confidence': '{:.1f} %'}), use_container_width=True, hide_index=True)

# ==========================================
# تب ۳: رأی‌گیری کمیته
# ==========================================
with tab_votes:
    st.subheader("🗳️ آخرین رأی‌گیری کمیته متخصصان")
    df_votes = load_robot_data() # استفاده از همان کش
    if not df_votes.empty:
        last = df_votes.iloc[-1]
        col1, col2 = st.columns(2)
        with col1:
            st.metric("تصمیم نهایی", "🟢 صعودی" if str(last['prediction']).strip() == 'UP' else "🔴 نزولی", f"اطمینان: {last['confidence']}%")
        with col2:
            if 'vote_details' in df_votes.columns and pd.notna(last['vote_details']):
                st.info(f"**جزئیات آرا:**\n\n" + str(last['vote_details']).replace(' | ', '\n\n🔹 '))
            else:
                st.warning("⏳ جزئیات آرا هنوز ثبت نشده است.")

# ==========================================
# تب ۴: وضعیت داده‌ها
# ==========================================
with tab_data:
    st.subheader("📡 وضعیت سلامت خط لوله داده‌ها")
    datasets = {
        "اخبار کریپتو": "https://raw.githubusercontent.com/mrzakarya/crypto-trading-bot/main/crypto_news_dataset.csv",
        "اخبار ایران": "https://raw.githubusercontent.com/mrzakarya/crypto-trading-bot/main/iran_market_news_dataset.csv"
    }
    cols = st.columns(2)
    for i, (name, url) in enumerate(datasets.items()):
        with cols[i]:
            try:
                temp = pd.read_csv(url)
                st.metric(name, f"{len(temp):,} رکورد", delta=f"آخرین: {pd.to_datetime(temp['date']).max().strftime('%Y-%m-%d')}" if 'date' in temp.columns else "بدون تاریخ")
            except:
                st.metric(name, "خطا", delta="داده‌ای یافت نشد")

st.markdown("---")
st.caption("🚀 ساخته شده با Streamlit | داده‌ها به صورت زنده از GitHub Actions و TGJU به‌روز می‌شوند")
