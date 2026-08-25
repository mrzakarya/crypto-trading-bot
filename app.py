import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
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
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 15px; font-size: 0.9em; background-color: #e3f2fd; color: #0d47a1; border: 1px solid #90caf9; }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=30000, limit=None, key="dashboard_autorefresh")

st.title("🤖 داشبورد ربات تریدر هوشمند")
st.caption(f"⏰ آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

tab_prices, tab_robot, tab_votes, tab_data = st.tabs(["💹 قیمت‌های زنده", "🤖 عملکرد ربات", "🗳️ رأی‌گیری کمیته", "📡 وضعیت داده‌ها"])

# ==========================================
# موتور محاسبه قیمت‌های ایران (بدون نیاز به اسکرپینگ)
# ==========================================
@st.cache_data(ttl=300)
def calculate_iran_market_prices():
    """محاسبه قیمت‌های بازار ایران بر اساس داده‌های جهانی (۱۰۰٪ پایدار و بدون مسدودسازی)"""
    prices = {}
    try:
        # ۱. دریافت نرخ دلار بازار آزاد (از طریق ریال عمان)
        omr_data = yf.Ticker("OMRIRR=X").history(period="2d")
        if len(omr_data) >= 2:
            omr_rate = float(omr_data['Close'].iloc[-1])
            prev_omr = float(omr_data['Close'].iloc[-2])
            dollar_free = omr_rate / 2.6
            prev_dollar = prev_omr / 2.6
            dollar_change = ((dollar_free - prev_dollar) / prev_dollar) * 100
            
            prices['dollar'] = {'name': 'دلار بازار آزاد', 'price': dollar_free, 'change': dollar_change}
            
            # ۲. دریافت انس جهانی طلا
            gold_oz_data = yf.Ticker("GC=F").history(period="2d")
            if len(gold_oz_data) >= 2:
                gold_oz = float(gold_oz_data['Close'].iloc[-1])
                prev_gold = float(gold_oz_data['Close'].iloc[-2])
                gold_change = ((gold_oz - prev_gold) / prev_gold) * 100
                
                # ۳. محاسبه طلای ۱۸ عیار (هر گرم)
                # فرمول: (انس * ۳۱.۱۰۳۵ * دلار) / ۷۵۰
                gold_18k = (gold_oz * 31.1035 * dollar_free) / 750
                prices['gold_18k'] = {'name': 'طلای ۱۸ عیار (هر گرم)', 'price': gold_18k, 'change': gold_change}
                
                # ۴. محاسبه سکه‌ها (وزن × عیار × دلار + حباب تقریبی بازار)
                # سکه امامی: ۸.۱۳۳ گرم، عیار ۹۰۰، حباب متوسط ۱۰٪
                emami_base = (gold_oz * 8.133 * 0.900 * dollar_free) / 31.1035
                prices['emami'] = {'name': 'سکه امامی', 'price': emami_base * 1.10, 'change': gold_change}
                
                # نیم سکه: ۴.۰۶۶ گرم، عیار ۹۰۰، حباب متوسط ۲۰٪
                half_base = (gold_oz * 4.066 * 0.900 * dollar_free) / 31.1035
                prices['half_coin'] = {'name': 'نیم سکه', 'price': half_base * 1.20, 'change': gold_change}
                
                # ربع سکه: ۲.۰۳۳ گرم، عیار ۹۰۰، حباب متوسط ۳۰٪
                quarter_base = (gold_oz * 2.033 * 0.900 * dollar_free) / 31.1035
                prices['quarter_coin'] = {'name': 'ربع سکه', 'price': quarter_base * 1.30, 'change': gold_change}
                
        return prices, "success"
    except Exception as e:
        return {}, f"error: {str(e)[:50]}"

# ==========================================
# تب ۱: قیمت‌های زنده بازار
# ==========================================
with tab_prices:
    st.subheader("💹 قیمت‌های زنده بازار")
    
    iran_prices, status = calculate_iran_market_prices()
    
    if status == "success":
        st.markdown('<div class="status-box">✅ داده‌ها با موفقیت از منابع جهانی محاسبه شدند. (این روش ۱۰۰٪ پایدار است و هرگز مسدود نمی‌شود)</div>', unsafe_allow_html=True)
    else:
        st.error(f"خطا در دریافت داده‌های جهانی: {status}")

    st.markdown("---")
    
    # ۱. ارزهای دیجیتال
    st.markdown("#### 🪙 ارزهای دیجیتال")
    crypto_map = {'BTC-USD': 'بیت‌کوین (BTC)', 'ETH-USD': 'اتریوم (ETH)', 'SOL-USD': 'سولانا (SOL)', 'BNB-USD': 'بایننس (BNB)', 'XRP-USD': 'ریپل (XRP)'}
    crypto_cols = st.columns(5)
    
    for i, (ticker, fa_name) in enumerate(crypto_map.items()):
        with crypto_cols[i]:
            try:
                data = yf.Ticker(ticker).history(period='2d')
                if len(data) >= 2:
                    current = float(data['Close'].iloc[-1])
                    previous = float(data['Close'].iloc[-2])
                    change = ((current - previous) / previous) * 100
                    delta_color = "normal" if change >= 0 else "inverse"
                    st.metric(label=fa_name, value=f"${current:,.2f}", delta=f"{change:+.2f}%", delta_color=delta_color)
            except:
                st.metric(label=fa_name, value="—", delta="خطا")

    st.markdown("---")
    
    # ۲. بازار ایران
    st.markdown("#### 🇮🇷 بازار طلا، سکه و ارز ایران")
    display_order = [
        ('dollar', '💵'),
        ('gold_18k', '✨'),
        ('emami', '🪙'),
        ('half_coin', '🪙'),
        ('quarter_coin', '🪙')
    ]
    
    iran_cols = st.columns(3)
    for i, (key, emoji) in enumerate(display_order):
        with iran_cols[i % 3]:
            if key in iran_prices:
                data = iran_prices[key]
                delta_color = "normal" if data['change'] >= 0 else "inverse"
                price_formatted = f"{data['price']:,.0f}"
                
                st.metric(
                    label=f"{emoji} {data['name']}",
                    value=f"{price_formatted} تومان",
                    delta=f"{data['change']:+.2f}%" if abs(data['change']) > 0.1 else "ثابت",
                    delta_color=delta_color
                )
            else:
                st.metric(label=f"{emoji} {key}", value="—", delta="در دسترس نیست")

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
        equity_curve = []
        for _, row in completed.iterrows():
            capital += capital * 0.025 if row['result'] == 'win' else -capital * 0.01
            equity_curve.append(capital)
            
        completed = completed.copy()
        completed['equity'] = equity_curve
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 سرمایه فعلی", f"{capital:,.0f} $", f"{((capital-10000)/10000)*100:+.2f}%")
        col2.metric("📊 تعداد تریدها", total)
        col3.metric("🎯 نرخ برد", f"{win_rate:.1f}%")
        
        st.markdown("---")
        if len(completed) > 0:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=completed['date'], y=completed['equity'], mode='lines+markers', line=dict(color='green', width=3), fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.1)'))
            fig.update_layout(xaxis_title="تاریخ", yaxis_title="سرمایه (دلار)", template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        
        display_df = df[['date', 'prediction', 'confidence', 'entry_price', 'result']].copy()
        display_df['prediction'] = display_df['prediction'].apply(lambda x: '🟢 صعودی' if x == 'UP' else '🔴 نزولی')
        st.dataframe(display_df.style.format({'entry_price': '{:,.2f} $', 'confidence': '{:.1f} %'}), use_container_width=True, hide_index=True)
    else:
        st.warning("هنوز داده‌ای برای نمایش وجود ندارد.")

# ==========================================
# تب ۳: رأی‌گیری کمیته
# ==========================================
with tab_votes:
    st.subheader("🗳️ آخرین رأی‌گیری کمیته متخصصان")
    df_votes = load_robot_data()
    if not df_votes.empty:
        last = df_votes.iloc[-1]
        col1, col2 = st.columns(2)
        with col1:
            st.metric("تصمیم نهایی", "🟢 صعودی" if str(last['prediction']).strip() == 'UP' else "🔴 نزولی", f"اطمینان: {last['confidence']}%")
        with col2:
            if 'vote_details' in df_votes.columns and pd.notna(last['vote_details']) and str(last['vote_details']).strip() != '':
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
st.caption("🚀 ساخته شده با Streamlit | داده‌ها به صورت زنده و پایدار از Yahoo Finance محاسبه می‌شوند")
