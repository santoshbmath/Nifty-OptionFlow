import streamlit as st
import pandas as pd
from curl_cffi import requests
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Nifty OptionFlow", layout="wide")

SYMBOL = "NIFTY"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
}

# --- DATE CALCULATION LOGIC ---
def get_upcoming_tuesday():
    today = datetime.today()
    days_ahead = 1 - today.weekday()
    if days_ahead < 0: 
        days_ahead += 7
    next_tuesday = today + timedelta(days=days_ahead)
    return next_tuesday.strftime("%d-%b-%Y")

@st.cache_data(ttl=15) 
def fetch_nse_data(symbol, expiry):
    api_url = f"https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol={symbol}&expiry={expiry}"
    try:
        session = requests.Session(impersonate="chrome110")
        session.headers.update(HEADERS)
        
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(1.5) 
        
        response = session.get(api_url, timeout=10)
        
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                st.error("⚠️ NSE blocked the request (returned HTML).")
                return None
        else:
            st.error(f"⚠️ Failed to fetch data: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        return None

def process_data(data, target_expiry):
    if not data or 'records' not in data or 'data' not in data['records']:
        return None, None
    
    underlying_value = data['records']['underlyingValue']
    
    oc_data = []
    for item in data['records']['data']:
        if item.get('expiryDates') == target_expiry or item.get('expiryDate') == target_expiry:
            row = {'strikePrice': item['strikePrice']}
            
            if 'CE' in item:
                row['CE_OI'] = item['CE'].get('openInterest', 0)
                row['CE_CHNG_OI'] = item['CE'].get('changeinOpenInterest', 0)
                row['CE_VOL'] = item['CE'].get('totalTradedVolume', 0)
            else:
                row['CE_OI'], row['CE_CHNG_OI'], row['CE_VOL'] = 0, 0, 0
                
            if 'PE' in item:
                row['PE_OI'] = item['PE'].get('openInterest', 0)
                row['PE_CHNG_OI'] = item['PE'].get('changeinOpenInterest', 0)
                row['PE_VOL'] = item['PE'].get('totalTradedVolume', 0)
            else:
                row['PE_OI'], row['PE_CHNG_OI'], row['PE_VOL'] = 0, 0, 0
                
            oc_data.append(row)
            
    df = pd.DataFrame(oc_data)
    
    if df.empty:
        st.error(f"⚠️ No data found for expiry date: {target_expiry}.")
        return None, underlying_value
    
    atm_strike = round(underlying_value / 50) * 50
    # Filter strictly to 11 strikes (+/- 250 points from ATM)
    df_filtered = df[(df['strikePrice'] >= atm_strike - 250) & (df['strikePrice'] <= atm_strike + 250)].copy()
    
    return df_filtered, underlying_value

def calculate_max_pain(df):
    strikes = df['strikePrice'].tolist()
    min_loss = float('inf')
    max_pain_strike = 0
    
    for s in strikes:
        total_loss = 0
        for index, row in df.iterrows():
            strike = row['strikePrice']
            ce_oi = row['CE_OI']
            pe_oi = row['PE_OI']
            
            if s > strike: 
                total_loss += (s - strike) * ce_oi
            if s < strike: 
                total_loss += (strike - s) * pe_oi
                
        if total_loss < min_loss:
            min_loss = total_loss
            max_pain_strike = s
            
    return max_pain_strike

def analyze_market(df, underlying, support, resistance):
    total_ce_chng_oi = df['CE_CHNG_OI'].sum()
    total_pe_chng_oi = df['PE_CHNG_OI'].sum()
    total_ce_vol = df['CE_VOL'].sum()
    total_pe_vol = df['PE_VOL'].sum()
    
    atm_strike = round(underlying / 50) * 50
    
    # 1. Base Direction Logic
    overall = {"trend": "SIDEWAYS", "reason": "Indecisive Volume and OI data across the chain."}
    if total_pe_chng_oi > total_ce_chng_oi and total_pe_vol > total_ce_vol:
        overall = {"trend": "BULLISH ↗", "reason": "Aggressive Put Writing & Strong Put Volumes."}
    elif total_ce_chng_oi > total_pe_chng_oi and total_ce_vol > total_pe_vol:
        overall = {"trend": "BEARISH ↘", "reason": "Aggressive Call Writing & Strong Call Volumes."}
        
    # 2. Support / Resistance Break/Reverse Logic
    dist_to_support = underlying - support
    dist_to_res = resistance - underlying
    sr_action = {"trend": "RANGE BOUND", "reason": "Price is trading safely between major Support and Resistance."}
    
    if dist_to_support < dist_to_res and dist_to_support < 50: 
        support_row = df[df['strikePrice'] == support].iloc[0]
        if support_row['PE_CHNG_OI'] > 0 and support_row['PE_VOL'] > support_row['CE_VOL']:
            sr_action = {"trend": "REVERSAL ↗", "reason": f"At Support ({support}): High Put addition indicates strong defense."}
        else:
            sr_action = {"trend": "BREAKDOWN ↘", "reason": f"At Support ({support}): Put Unwinding suggests support is failing."}
            
    elif dist_to_res < dist_to_support and dist_to_res < 50: 
        res_row = df[df['strikePrice'] == resistance].iloc[0]
        if res_row['CE_CHNG_OI'] > 0 and res_row['CE_VOL'] > res_row['PE_VOL']:
            sr_action = {"trend": "REVERSAL ↘", "reason": f"At Resistance ({resistance}): High Call addition indicates strong rejection."}
        else:
            sr_action = {"trend": "BREAKOUT ↗", "reason": f"At Resistance ({resistance}): Call Unwinding suggests resistance is failing."}

    # 3. ATM (Immediate Next Strike) Logic
    atm_action = {"trend": "NEUTRAL", "reason": f"ATM ({atm_strike}): Action is mixed or stabilizing."}
    if atm_strike in df['strikePrice'].values:
        atm_row = df[df['strikePrice'] == atm_strike].iloc[0]
        ce_chng = atm_row['CE_CHNG_OI']
        pe_chng = atm_row['PE_CHNG_OI']
        ce_vol = atm_row['CE_VOL']
        pe_vol = atm_row['PE_VOL']
        
        if ce_chng < 0 and pe_chng > 0:
            atm_action = {"trend": "BREAKOUT ↗", "reason": f"ATM ({atm_strike}): Call unwinding (panic) while Put writers add OI."}
        elif pe_chng < 0 and ce_chng > 0:
            atm_action = {"trend": "BREAKDOWN ↘", "reason": f"ATM ({atm_strike}): Put unwinding (panic) while Call writers add OI."}
        elif ce_chng > pe_chng and ce_vol > pe_vol:
            atm_action = {"trend": "RESISTANCE ↘", "reason": f"ATM ({atm_strike}): Strong Call writing. Immediate resistance building."}
        elif pe_chng > ce_chng and pe_vol > ce_vol:
            atm_action = {"trend": "SUPPORT ↗", "reason": f"ATM ({atm_strike}): Strong Put writing. Immediate support building."}

    return overall, sr_action, atm_action

# --- PLOTLY CHART HELPER ---
def create_bar_chart(df, ce_col, pe_col, title, atm_strike):
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['strikePrice'], 
        y=df[ce_col],
        name='Call (CE)',
        marker_color='rgba(231, 76, 60, 0.85)' 
    ))
    
    fig.add_trace(go.Bar(
        x=df['strikePrice'], 
        y=df[pe_col],
        name='Put (PE)',
        marker_color='rgba(39, 174, 96, 0.85)'
    ))
    
    fig.update_layout(
        title=title,
        barmode='group',
        xaxis=dict(
            title="Strike Price",
            type='linear',
            tickmode='array',
            tickvals=df['strikePrice'].tolist(),
            ticktext=[str(strike) for strike in df['strikePrice']] 
        ),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=350
    )
    
    fig.add_vline(
        x=atm_strike, 
        line_dash="dot", 
        line_color="gray", 
        line_width=2,
        annotation_text="ATM", 
        annotation_position="top left"
    )
    
    return fig


# --- UI LAYOUT ---
title_col, settings_col = st.columns([5, 1])

default_expiry = get_upcoming_tuesday()

with settings_col:
    st.write("") 
    with st.popover("⚙️ Settings"):
        user_expiry = st.text_input("Target Expiry", value=default_expiry, help="Format: dd-MMM-yyyy")
        refresh_rate = st.number_input("Refresh Rate (Seconds)", min_value=10, value=60, step=5)
        st.caption(f"Next refresh in {refresh_rate} seconds...")

with title_col:
    st.title("Nifty OptionFlow")
    st.caption("*Live OI, Volume & Breakout Intelligence*")
    
    current_time = datetime.now().strftime("%I:%M:%S %p")
    st.markdown(f"**Target Expiry:** `{user_expiry}` | **Range:** +/- 5 Strikes from ATM (11 Total) | **Last Refreshed:** `{current_time}`")

data = fetch_nse_data(SYMBOL, user_expiry)
df, current_price = process_data(data, user_expiry)

if df is not None and not df.empty:
    
    atm_strike = round(current_price / 50) * 50
    
    # --- MAJOR vs IMMEDIATE S/R LOGIC ---
    # Major (Max OI) Support & Resistance
    support_max = df.loc[df['PE_OI'].idxmax()]['strikePrice']
    resistance_max = df.loc[df['CE_OI'].idxmax()]['strikePrice']
    
    # Immediate (Near ATM) Support & Resistance
    # Nearest support is the highest strike <= current price
    sup_near_df = df[df['strikePrice'] <= current_price]
    support_near = sup_near_df['strikePrice'].max() if not sup_near_df.empty else support_max
    
    # Nearest resistance is the lowest strike >= current price
    res_near_df = df[df['strikePrice'] >= current_price]
    resistance_near = res_near_df['strikePrice'].min() if not res_near_df.empty else resistance_max

    max_pain = calculate_max_pain(df)
    
    # We pass the Major levels (Max OI) for structural boundary intelligence
    overall, sr_action, atm_action = analyze_market(df, current_price, support_max, resistance_max)
    
    # Format strings to show 1 or 2 targets depending on overlap
    sup_display = f"{support_near:,.0f} / {support_max:,.0f}" if support_near != support_max else f"{support_max:,.0f}"
    res_display = f"{resistance_near:,.0f} / {resistance_max:,.0f}" if resistance_near != resistance_max else f"{resistance_max:,.0f}"
    
    # --- UI METRICS ---
    st.subheader("Market Dynamics")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("NIFTY Underlying", f"{current_price:,.2f}")
    col2.metric("Support (Near / Max)", sup_display)
    col3.metric("Resistance (Near / Max)", res_display)
    col4.metric("Max Pain Strike", f"{max_pain:,.0f}")
    
    st.markdown("### 🧭 Trading Insights")
    
    insight_col1, insight_col2, insight_col3 = st.columns(3)
    
    def get_trend_color(trend_text):
        if "BULLISH" in trend_text or "↗" in trend_text or "SUPPORT" in trend_text:
            return "🟢" 
        elif "BEARISH" in trend_text or "↘" in trend_text or "RESISTANCE" in trend_text or "BREAKDOWN" in trend_text:
            return "🔴" 
        else:
            return "🟡" 
            
    with insight_col1:
        with st.container(border=True):
            st.markdown("**Overall Trend**")
            st.subheader(f"{get_trend_color(overall['trend'])} {overall['trend']}")
            st.caption(f"*{overall['reason']}*")
            
    with insight_col2:
        with st.container(border=True):
            st.markdown("**Trend at ATM**")
            st.subheader(f"{get_trend_color(atm_action['trend'])} {atm_action['trend']}")
            st.caption(f"*{atm_action['reason']}*")
            
    with insight_col3:
        with st.container(border=True):
            st.markdown("**Trend at Major S/R**")
            st.subheader(f"{get_trend_color(sr_action['trend'])} {sr_action['trend']}")
            st.caption(f"*{sr_action['reason']}*")

    
    # --- VISUAL DATA GRAPHS ---
    st.markdown("---")
    st.subheader("Visual Option Chain (11 Strikes)")
    
    chart_col1, chart_col2, chart_col3 = st.columns(3)
    
    with chart_col1:
        fig_oi = create_bar_chart(df, 'CE_OI', 'PE_OI', "Total Open Interest (OI)", atm_strike)
        st.plotly_chart(fig_oi, use_container_width=True)
        
    with chart_col2:
        fig_chng_oi = create_bar_chart(df, 'CE_CHNG_OI', 'PE_CHNG_OI', "Change in OI", atm_strike)
        st.plotly_chart(fig_chng_oi, use_container_width=True)
        
    with chart_col3:
        fig_vol = create_bar_chart(df, 'CE_VOL', 'PE_VOL', "Traded Volume", atm_strike)
        st.plotly_chart(fig_vol, use_container_width=True)
        
    # --- DATA TABLE ---
    st.markdown("---")
    with st.expander("Show Raw Data Table"):
        display_df = df[['CE_VOL', 'CE_CHNG_OI', 'CE_OI', 'strikePrice', 'PE_OI', 'PE_CHNG_OI', 'PE_VOL']].copy()
        
        def highlight_strikes(row):
            sp = row['strikePrice']
            # Highlight ALL significant levels (Near and Max)
            if sp == support_max or sp == support_near:
                return ['background-color: rgba(39, 174, 96, 0.35)'] * len(row)  
            elif sp == resistance_max or sp == resistance_near:
                return ['background-color: rgba(231, 76, 60, 0.35)'] * len(row)  
            elif sp == atm_strike:
                return ['background-color: rgba(149, 165, 166, 0.35)'] * len(row) 
            return [''] * len(row)
            
        st.dataframe(display_df.style.apply(highlight_strikes, axis=1), use_container_width=True)
    
else:
    st.warning("Awaiting market data or the market is closed/unavailable.")

time.sleep(refresh_rate)
st.rerun()