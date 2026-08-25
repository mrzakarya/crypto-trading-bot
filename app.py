import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# تنظیمات صفحه
st.set_page_config(page_title="داشبورد ربات تریدر هوشمند", page_icon="🤖", layout="wide")

st.title("🤖 داشبورد عملکرد ربات تریدر هوشمند (Paper Trading)")
st.markdown("این داشبورد به صورت زنده داده‌ها را از مخزن گیت‌هاب می‌خواند.")

# بارگذاری داده‌ها
@st.cache_data(ttl=3600) # کش کردن داده‌ها برای ۱ ساعت
def load_data():
    try:
        # خواندن مستقیم از گیت‌هاب (آدرس را با نام کاربری خود جایگزین کنید)
        url = "https://raw.githubusercontent.com/mrzakarya/crypto-trading-bot/main/paper_trading_log.csv"
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"خطا در بارگذاری داده‌ها: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # ==========================================
    # ۱. محاسبه متریک‌های کلیدی (KPIs)
    # ==========================================
    completed_trades = df[df['result'].isin(['win', 'loss'])]
    total_trades = len(completed_trades)
    wins = len(completed_trades[completed_trades['result'] == 'win'])
    losses = len(completed_trades[completed_trades['result'] == 'loss'])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    # محاسبه منحنی سرمایه (Equity Curve)
    INITIAL_CAPITAL = 10000
    capital = INITIAL_CAPITAL
    equity_curve = []
    
    for _, row in completed_trades.iterrows():
        if row['result'] == 'win':
            capital += capital * 0.025  # 2.5% سود
        else:
            capital -= capital * 0.01   # 1% ضرر
        equity_curve.append(capital)
        
    completed_trades = completed_trades.copy()
    completed_trades['equity'] = equity_curve
    current_profit_pct = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

    # ==========================================
    # ۲. نمایش متریک‌ها در بالای صفحه
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("سرمایه فعلی (فرضی)", f"{capital:,.0f} $", f"{current_profit_pct:+.2f}%")
    col2.metric("تعداد کل تریدها", total_trades)
    col3.metric("نرخ برد (Win Rate)", f"{win_rate:.1f}%")
    col4.metric("آخرین پیش‌بینی", df.iloc[-1]['prediction'], delta="در انتظار نتیجه" if df.iloc[-1]['result'] == 'pending' else df.iloc[-1]['result'])

    # ==========================================
    # نمایش جزئیات رأی‌گیری آخرین پیش‌بینی
    # ==========================================
    st.subheader("🗳️ آخرین رأی‌گیری کمیته متخصصان")
    last_pred = df.iloc[-1]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("تصمیم نهایی", 
                  "🟢 صعودی (UP)" if last_pred['prediction'] == 'UP' else "🔴 نزولی (DOWN)",
                  f"اطمینان: {last_pred['confidence']}%")
    
    with col2:
        st.info(f"**جزئیات آرا:**\n\n{last_pred['vote_details']}")
    st.markdown("---")

    # ==========================================
    # ۳. نمودار منحنی سرمایه (Equity Curve)
    # ==========================================
    if len(completed_trades) > 0:
        st.subheader("📈 منحنی رشد سرمایه (Equity Curve)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=completed_trades['date'], 
            y=completed_trades['equity'], 
            mode='lines+markers', 
            name='سرمایه',
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

    # ==========================================
    # ۴. جدول جزئیات تریدها
    # ==========================================
    st.subheader("📋 کارنامه تفصیلی پیش‌بینی‌ها")
    
    # رنگ‌بندی جدول
    def color_results(val):
        if val == 'win': return 'color: green; font-weight: bold'
        if val == 'loss': return 'color: red; font-weight: bold'
        if val == 'pending': return 'color: orange; font-weight: bold'
        return ''

    display_df = df[['date', 'prediction', 'confidence', 'entry_price', 'exit_price', 'price_change_pct', 'result']].copy()
    display_df['prediction'] = display_df['prediction'].apply(lambda x: '🟢 صعودی' if x == 'UP' else '🔴 نزولی')
    
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
    st.warning("هنوز داده‌ای برای نمایش وجود ندارد. لطفاً صبر کنید تا ربات اولین پیش‌بینی‌ها را ثبت کند.")

# فوتر
st.markdown("---")
st.caption("ساخته شده با Streamlit | داده‌ها به صورت زنده از GitHub Actions به‌روز می‌شوند.")
