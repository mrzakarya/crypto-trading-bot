import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime

# ==========================================
# تنظیمات اولیه صفحه
# ==========================================
st.set_page_config(page_title="داشبورد ربات تریدر هوشمند", page_icon="🤖", layout="wide")

# 🔥 فعال‌سازی راست‌چین (RTL) برای کل صفحه
st.markdown("""
<style>
    /* راست‌چین کردن کل اپلیکیشن */
    .stApp, .block-container, [data-testid="stVerticalBlock"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* راست‌چین کردن متریک‌ها */
    [data-testid="stMetric"] {
        direction: rtl !important;
        text-align: right !important;
    }
    [data-testid="stMetricLabel"] {
        text-align: right !important;
    }
    [data-testid="stMetricValue"] {
        text-align: right !important;
    }
    
    /* راست‌چین کردن تب‌ها */
    .stTabs [data-baseweb="tab-list"] {
        direction: rtl;
        gap: 8px;
    }
    
    /* راست‌چین کردن جدول‌ها */
    .dataframe {
        direction: rtl !important;
    }
    
    /* راست‌چین کردن هدرها */
    h1, h2, h3, h4, p, span, div {
        text-align: right !important;
    }
</style>
""", unsafe_allow_html=True)

# رفرش خودکار هر ۳۰ ثانیه
st_autorefresh(interval=30000, limit=None, key="dashboard_autorefresh")

st.title("🤖 داشبورد ربات تریدر هوشمند")
st.caption(f"⏰ آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==========================================
# تعریف تب‌های اصلی
# ==========================================
tab_prices, tab_robot, tab_votes, tab_data = st.tabs([
    "💹 قیمت‌های زنده بازار",
    "🤖 عملکرد ربات",
    "🗳️ رأی‌گیری کمیته",
    "📡 وضعیت داده‌ها"
])

# ==========================================
# تب ۱: قیمت‌های زنده بازار
# ==========================================
with tab_prices:
    st.subheader("💹 قیمت‌های زنده بازار")
    st.caption("⏱️ به‌روزرسانی خودکار هر ۵ دقیقه | داده‌ها از Yahoo Finance")
    
    @st.cache_data(ttl=300)
    def get_live_prices():
        """دریافت قیمت‌های زنده با fallback برای طلا و دلار ایران"""
        prices = {}
        
        # ۱. ارزهای دیجیتال
        crypto_map = {
            'BTC-USD': ('بیت‌کوین', 'BTC'),
            'ETH-USD': ('اتریوم', 'ETH'),
            'SOL-USD': ('سولانا', 'SOL'),
            'BNB-USD': ('بایننس کوین', 'BNB'),
            'XRP-USD': ('ریپل', 'XRP'),
            'ADA-USD': ('کاردانو', 'ADA'),
            'DOGE-USD': ('دوج‌کوین', 'DOGE')
        }
        
        for ticker, (fa_name, en_name) in crypto_map.items():
            try:
                data = yf.Ticker(ticker).history(period='5d')
                if len(data) >= 2:
                    current = float(data['Close'].iloc[-1])
                    previous = float(data['Close'].iloc[-2])
                    change = ((current - previous) / previous) * 100
                    prices[f'crypto_{en_name}'] = {
                        'fa_name': fa_name,
                        'price': current,
                        'change': change,
                        'currency': '$',
                        'format': ',.2f'
                    }
            except Exception as e:
                continue
        
        # ۲. انس جهانی طلا (با fallback)
        gold_tickers = ['GC=F', 'GLD']  # GC=F = فیوچر طلا، GLD = ETF طلا
        for gold_ticker in gold_tickers:
            try:
                data = yf.Ticker(gold_ticker).history(period='5d')
                if len(data) >= 2:
                    current = float(data['Close'].iloc[-1])
                    previous = float(data['Close'].iloc[-2])
                    change = ((current - previous) / previous) * 100
                    prices['gold_oz'] = {
                        'fa_name': 'انس جهانی طلا',
                        'price': current,
                        'change': change,
                        'currency': '$',
                        'format': ',.2f'
                    }
                    break
            except:
                continue
        
        # ۳. انس جهانی نقره
        try:
            data = yf.Ticker("SI=F").history(period='5d')
            if len(data) >= 2:
                current = float(data['Close'].iloc[-1])
                previous = float(data['Close'].iloc[-2])
                change = ((current - previous) / previous) * 100
                prices['silver_oz'] = {
                    'fa_name': 'انس جهانی نقره',
                    'price': current,
                    'change': change,
                    'currency': '$',
                    'format': ',.2f'
                }
        except:
            pass
        
        # ۴. دلار بازار ایران (از ریال عمان ÷ 2.6)
        try:
            data = yf.Ticker("OMRIRR=X").history(period='5d')
            if len(data) >= 2:
                omr_to_irr = float(data['Close'].iloc[-1])
                previous_omr = float(data['Close'].iloc[-2])
                
                # دلار بازار آزاد ایران = نرخ ریال عمان ÷ 2.6
                dollar_iran = omr_to_irr / 2.6
                dollar_previous = previous_omr / 2.6
                change = ((dollar_iran - dollar_previous) / dollar_previous) * 100
                
                prices['dollar_iran'] = {
                    'fa_name': 'دلار بازار آزاد ایران',
                    'price': dollar_iran,
                    'change': change,
                    'currency': 'تومان',
                    'format': ',.0f',
                    'note': '💡 محاسبه از نرخ ریال عمان ÷ 2.6'
                }
        except:
            pass
        
        # ۵. طلای ۱۸ عیار ایران (محاسبه از انس جهانی + دلار ایران)
        if 'gold_oz' in prices and 'dollar_iran' in prices:
            try:
                gold_oz_usd = prices['gold_oz']['price']
                dollar_rate = prices['dollar_iran']['price']
                # فرمول: (انس × 31.1035 گرم × نرخ دلار ÷ 750) × 1000 ÷ 1000
                gold_18k = (gold_oz_usd * 31.1035 * dollar_rate) / 750
                prices['gold_18k'] = {
                    'fa_name': 'طلای ۱۸ عیار (هر گرم)',
                    'price': gold_18k,
                    'change': prices['gold_oz']['change'],
                    'currency': 'تومان',
                    'format': ',.0f',
                    'note': '💡 محاسبه تقریبی (بدون احتساب حباب و اجرت)'
                }
            except:
                pass
        
        return prices
    
    prices = get_live_prices()
    
    if prices:
        # بخش ۱: ارزهای دیجیتال
        st.markdown("#### 🪙 ارزهای دیجیتال")
        crypto_names = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE']
        crypto_cols = st.columns(len(crypto_names))
        
        for i, name in enumerate(crypto_names):
            with crypto_cols[i]:
                data = prices.get(f'crypto_{name}')
                if data and data.get('price'):
                    delta_color = "normal" if data['change'] >= 0 else "inverse"
                    st.metric(
                        label=f"{data['fa_name']} ({name})",
                        value=f"${data['price']:,.2f}",
                        delta=f"{data['change']:+.2f}%",
                        delta_color=delta_color
                    )
        
        st.markdown("---")
        
        # بخش ۲: فلزات گرانبها + دلار
        st.markdown("#### 🥇 فلزات گرانبها و ارز")
        metal_cols = st.columns(4)
        metal_items = [
            ('gold_oz', '🥇'),
            ('silver_oz', '🥈'),
            ('gold_18k', '💰'),
            ('dollar_iran', '💵')
        ]
        
        for i, (key, emoji) in enumerate(metal_items):
            with metal_cols[i]:
                data = prices.get(key)
                if data and data.get('price'):
                    delta_color = "normal" if data['change'] >= 0 else "inverse"
                    price_formatted = f"{data['price']:{data['format']}}"
                    st.metric(
                        label=f"{emoji} {data['fa_name']}",
                        value=f"{price_formatted} {data['currency']}",
                        delta=f"{data['change']:+.2f}%",
                        delta_color=delta_color
                    )
                    if 'note' in data:
                        st.caption(data['note'])
                else:
                    st.metric(label=f"{emoji}", value="—", delta="داده در دسترس نیست")
    else:
        st.warning("⚠️ در حال حاضر امکان دریافت قیمت‌های زنده وجود ندارد.")

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
        # محاسبه متریک‌ها
        completed_trades = df[df['result'].isin(['win', 'loss'])]
        total_trades = len(completed_trades)
        wins = len(completed_trades[completed_trades['result'] == 'win'])
        losses = len(completed_trades[completed_trades['result'] == 'loss'])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        INITIAL_CAPITAL = 10000
        capital = INITIAL_CAPITAL
        equity_curve = []
        
        for _, row in completed_trades.iterrows():
            if row['result'] == 'win':
                capital += capital * 0.025
            else:
                capital -= capital * 0.01
            equity_curve.append(capital)
        
        completed_trades = completed_trades.copy()
        completed_trades['equity'] = equity_curve
        current_profit_pct = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
        
        # نمایش متریک‌ها
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 سرمایه فعلی", f"{capital:,.0f} $", f"{current_profit_pct:+.2f}%")
        col2.metric("📊 تعداد تریدها", total_trades)
        col3.metric("🎯 نرخ برد", f"{win_rate:.1f}%")
        col4.metric("🔮 آخرین پیش‌بینی", 
                    "🟢 صعودی" if df.iloc[-1]['prediction'] == 'UP' else "🔴 نزولی")
        
        st.markdown("---")
        
        # نمودار Equity Curve
        if len(completed_trades) > 0:
            st.markdown("#### 📈 منحنی رشد سرمایه")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=completed_trades['date'], 
                y=completed_trades['equity'], 
                mode='lines+markers', 
                line=dict(color='green', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 0, 0.1)'
            ))
            fig.update_layout(
                xaxis_title="تاریخ",
                yaxis_title="سرمایه (دلار)",
                template="plotly_dark",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # جدول کارنامه
        st.markdown("#### 📋 کارنامه تفصیلی")
        display_df = df[['date', 'prediction', 'confidence', 'entry_price', 'exit_price', 'price_change_pct', 'result']].copy()
        display_df['prediction'] = display_df['prediction'].apply(lambda x: '🟢 صعودی' if x == 'UP' else '🔴 نزولی')
        
        def color_results(val):
            if val == 'win': return 'color: green; font-weight: bold'
            if val == 'loss': return 'color: red; font-weight: bold'
            if val == 'pending': return 'color: orange; font-weight: bold'
            return ''
        
        st.dataframe(
            display_df.style.applymap(color_results, subset=['result']).format({
                'entry_price': '{:,.2f} $',
                'exit_price': '{:,.2f} $',
                'price_change_pct': '{:+.2f} %',
                'confidence': '{:.1f} %'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("هنوز داده‌ای برای نمایش وجود ندارد.")

# ==========================================
# تب ۳: رأی‌گیری کمیته
# ==========================================
with tab_votes:
    st.subheader("🗳️ آخرین رأی‌گیری کمیته متخصصان")
    
    @st.cache_data(ttl=3600)
    def load_robot_data_for_votes():
        try:
            url = "https://raw.githubusercontent.com/mrzakarya/crypto-trading-bot/main/paper_trading_log.csv"
            return pd.read_csv(url)
        except:
            return pd.DataFrame()
    
    df_votes = load_robot_data_for_votes()
    
    if not df_votes.empty:
        last_pred = df_votes.iloc[-1]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("تصمیم نهایی", 
                      "🟢 صعودی (UP)" if str(last_pred['prediction']).strip() == 'UP' else "🔴 نزولی (DOWN)",
                      f"اطمینان: {last_pred['confidence']}%")
        
        with col2:
            if 'vote_details' in df_votes.columns and pd.notna(last_pred['vote_details']) and str(last_pred['vote_details']).strip() != '':
                raw_votes = str(last_pred['vote_details'])
                formatted_votes = raw_votes.replace(' | ', '\n\n🔹 ')
                st.info(f"**جزئیات آرا:**\n\n🔹 {formatted_votes}")
            else:
                st.warning("⏳ جزئیات آرا هنوز ثبت نشده است.")
    else:
        st.warning("هنوز داده‌ای برای نمایش وجود ندارد.")

# ==========================================
# تب ۴: وضعیت داده‌ها
# ==========================================
with tab_data:
    st.subheader("📡 وضعیت سلامت خط لوله داده‌ها")
    
    DATASETS = {
        "اخبار کریپتو": "https://raw.githubusercontent.com/mrzakarya/crypto-trading-bot/main/crypto_news_dataset.csv",
        "اخبار بازار ایران": "https://raw.githubusercontent.com/mrzakarya/crypto-trading-bot/main/iran_market_news_dataset.csv",
        "قیمت‌های بازار ایران": "https://raw.githubusercontent.com/mrzakarya/crypto-trading-bot/main/iran_market_prices.csv"
    }
    
    def get_dataset_stats(url):
        try:
            temp_df = pd.read_csv(url)
            if temp_df.empty:
                return {"status": "⚠️ خالی", "count": 0, "last_date": "بدون داده"}
            
            count = len(temp_df)
            if 'date' in temp_df.columns:
                last_date = pd.to_datetime(temp_df['date'], errors='coerce').max()
                last_date_str = last_date.strftime('%Y-%m-%d') if pd.notna(last_date) else "نامشخص"
            else:
                last_date_str = "ستون تاریخ یافت نشد"
                
            return {"status": "✅ فعال", "count": count, "last_date": last_date_str}
        except Exception as e:
            return {"status": "❌ خطا", "count": 0, "last_date": str(e)[:30] + "..."}
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    datasets_list = list(DATASETS.items())
    for i, (name, url) in enumerate(datasets_list):
        stats = get_dataset_stats(url)
        
        with [col_d1, col_d2, col_d3][i]:
            st.metric(
                label=name,
                value=f"{stats['count']:,} رکورد",
                delta=f"آخرین به‌روزرسانی: {stats['last_date']}"
            )
            if stats['status'] != "✅ فعال":
                st.caption(f"وضعیت: {stats['status']}")

# فوتر
st.markdown("---")
st.caption("🚀 ساخته شده با Streamlit | داده‌ها به صورت زنده از GitHub Actions به‌روز می‌شوند")
