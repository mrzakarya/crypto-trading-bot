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
    /* استایل خاص برای باکس وضعیت اتصال */
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 15px; font-size: 0.9em; }
    .status-success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .status-error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=30000, limit=None, key="dashboard_autorefresh")

st.title("🤖 داشبورد ربات تریدر هوشمند")
st.caption(f"⏰ آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

tab_prices, tab_robot, tab_votes, tab_data = st.tabs(["💹 قیمت‌های زنده", "🤖 عملکرد ربات", "🗳️ رأی‌گیری کمیته", "📡 وضعیت داده‌ها"])

# ==========================================
# تابع اسکرپینگ فوق‌العاده مقاوم از IranJib
# ==========================================
@st.cache_data(ttl=300)  # کش ۵ دقیقه‌ای
def get_iran_prices_robust():
    """دریافت قیمت‌ها از IranJib با هدرهای مرورگر واقعی برای دور زدن فایروال"""
    url = "https://www.iranjib.ir/showgroup/23/realtime_price/"
    
    # هدرهای دقیق یک مرورگر کروم در ویندوز برای فریب دادن فایروال
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Cache-Control": "max-age=0"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # پیدا کردن تمام ردیف‌های جدول
        rows = soup.find_all('tr')
        results = {}
        status = "success"
        error_msg = ""
        
        # کلمات کلیدی برای جستجو در جدول
        targets = {
            'دلار آمریکا': 'dollar',
            'یورو': 'euro',
            'سکه امامی': 'emami',
            'نیم سکه': 'half_coin',
            'ربع سکه': 'quarter_coin',
            'طلای 18 عیار': 'gold_18k'
        }
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                name_text = cells[0].get_text(strip=True)
                
                for target_key, target_id in targets.items():
                    if target_key in name_text and target_id not in results:
                        # استخراج قیمت (حذف کاما و فاصله)
                        price_str = cells[1].get_text(strip=True).replace(',', '').replace(' ', '')
                        # استخراج درصد تغییر (حذف + و % و فاصله)
                        change_str = cells[2].get_text(strip=True).replace('+', '').replace('%', '').replace('−', '-').strip()
                        
                        try:
                            price = float(price_str)
                            change = float(change_str) if change_str else 0.0
                            results[target_id] = {
                                'name': target_key,
                                'price': price,
                                'change': change
                            }
                        except ValueError:
                            pass # اگر تبدیل عدد ناموفق بود، رد می‌شود
        
        if len(results) < 3: # اگر کمتر از ۳ مورد پیدا شد، یعنی احتمالاً صفحه بلاک شده
            status = "blocked"
            error_msg = "فایروال سایت مبدا، IP سرور استریم‌لیت را مسدود کرده است."
            
        return results, status, error_msg
        
    except requests.exceptions.RequestException as e:
        return {}, "error", f"خطای شبکه: {str(e)[:50]}"
    except Exception as e:
        return {}, "error", f"خطای ناشناخته: {str(e)[:50]}"


# ==========================================
# تب ۱: قیمت‌های زنده بازار
# ==========================================
with tab_prices:
    st.subheader("💹 قیمت‌های زنده بازار")
    
    # ۱. دریافت قیمت‌های ایران
    iran_prices, conn_status, conn_error = get_iran_prices_robust()
    
    # نمایش وضعیت اتصال (برای دیباگ شفاف)
    if conn_status == "success":
        st.markdown('<div class="status-box status-success">✅ اتصال به IranJib موفقیت‌آمیز بود. داده‌ها به‌روز هستند.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-box status-error">⚠️ خطا در دریافت داده از IranJib: {conn_error}<br>💡 <b>راه‌حل:</b> این یک محدودیت امنیتی از سمت سایت‌های ایرانی برای IPهای خارجی (AWS) است. در این حالت، قیمت‌ها از منبع جایگزین محاسبه می‌شوند.</div>', unsafe_allow_html=True)
        
        # 🔥 FALLBACK (منبع جایگزین): اگر IranJib بلاک کرد، از محاسبه تقریبی استفاده کن
        if not iran_prices:
            try:
                # دریافت دلار از OMRIRR
                omr_data = yf.Ticker("OMRIRR=X").history(period='2d')
                if len(omr_data) >= 2:
                    usd_estimate = (float(omr_data['Close'].iloc[-1]) / 2.6)
                    iran_prices['dollar'] = {'name': 'دلار آمریکا (تخمینی)', 'price': usd_estimate, 'change': 0.0}
                
                # دریافت انس طلا برای محاسبه طلای ۱۸ عیار
                gold_data = yf.Ticker("GC=F").history(period='2d')
                if len(gold_data) >= 2 and 'dollar' in iran_prices:
                    gold_oz = float(gold_data['Close'].iloc[-1])
                    gold_18k_estimate = (gold_oz * 31.1035 * iran_prices['dollar']['price']) / 750
                    iran_prices['gold_18k'] = {'name': 'طلای ۱۸ عیار (تخمینی)', 'price': gold_18k_estimate, 'change': 0.0}
            except:
                pass

    st.markdown("---")
    
    # ۲. نمایش ارزهای دیجیتال (همیشه پایدار)
    st.markdown("#### 🪙 ارزهای دیجیتال (Yahoo Finance)")
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
    
    # ۳. نمایش بازار ایران
    st.markdown("#### 🇮🇷 بازار طلا، سکه و ارز ایران")
    
    # تعریف آیتم‌هایی که می‌خواهیم نمایش دهیم و ترتیب آن‌ها
    display_order = [
        ('dollar', '💵'),
        ('euro', '💶'),
        ('emami', '🪙'),
        ('half_coin', '🪙'),
        ('quarter_coin', '🪙'),
        ('gold_18k', '✨')
    ]
    
    iran_cols = st.columns(3) # ۳ ستون برای نمایش زیباتر
    
    for i, (key, emoji) in enumerate(display_order):
        with iran_cols[i % 3]:
            if key in iran_prices:
                data = iran_prices[key]
                delta_color = "normal" if data['change'] >= 0 else "inverse"
                # فرمت‌بندی قیمت با جداکننده هزارگان
                price_formatted = f"{data['price']:,.0f}"
                
                st.metric(
                    label=f"{emoji} {data['name']}",
                    value=f"{price_formatted} تومان",
                    delta=f"{data['change']:+.2f}%" if data['change'] != 0 else "ثابت",
                    delta_color=delta_color
                )
            else:
                st.metric(label=f"{emoji} {key}", value="—", delta="داده در دسترس نیست")

# ==========================================
# تب ۲: عملکرد ربات (کد قبلی شما حفظ شده)
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
st.caption("🚀 ساخته شده با Streamlit | داده‌ها به صورت زنده از GitHub Actions و IranJib به‌روز می‌شوند")
