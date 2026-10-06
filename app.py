import streamlit as st
import yfinance as ticker_data
import pandas as pd
import numpy as np
import requests

# Telegram Alert Function
def send_telegram_alert(token, chat_id, message):
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception:
        return False

# Streamlit Page Config
st.set_page_config(page_title="Traders Ankit - Institutional Suite", page_icon="📈", layout="wide")

# Header Section
st.title("📈 TRADERS ANKIT")
st.caption("Institutional Order Flow, CVD, FVG, GEX & Position Sizing Suite | Created for Ankit")

# Sidebar Setup - Asset
st.sidebar.header("⚙️ Asset Settings")
symbol = st.sidebar.text_input("एसेट सिंबल (Symbol):", "BTC-USD")
st.sidebar.caption("उदा: BTC-USD, ETH-USD, GC=F (Gold), CL=F (Oil), RELIANCE.NS")

# Sidebar Setup - Risk Management
st.sidebar.header("🛡️ Risk Management Settings")
total_capital = st.sidebar.number_input("आपकी कुल पूंजी ($ / ₹):", min_value=10.0, value=1000.0, step=50.0)
risk_per_trade_pct = st.sidebar.slider("प्रति ट्रेड रिस्क (% Risk per Trade):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

# Sidebar Setup - Telegram Credentials
st.sidebar.header("📱 Telegram Bot Setup")
tg_token = st.sidebar.text_input("Bot Token:", type="password", placeholder="123456789:ABCdef...")
tg_chat_id = st.sidebar.text_input("Chat ID:", placeholder="987654321")

analyze_btn = st.sidebar.button("Run Traders Ankit Engine 🚀")

if analyze_btn:
    with st.spinner('Traders Ankit Engine एनालाइज़ कर रहा है...'):
        try:
            # Fetch Market Data
            df = ticker_data.download(symbol, period="1mo", interval="1d")
            
            if len(df) < 14:
                st.error("डेटा उपलब्ध नहीं है या गलत सिंबल है।")
            else:
                close = df['Close'].squeeze()
                high = df['High'].squeeze()
                low = df['Low'].squeeze()
                open_p = df['Open'].squeeze()
                volume = df['Volume'].squeeze()

                current_price = float(close.iloc[-1])
                prev_close = float(close.iloc[-2])

                # 1. DELTA FOOTPRINT & CVD
                price_range = high - low
                price_range = price_range.replace(0, 1e-5)
                buy_vol = volume * ((close - low) / price_range)
                sell_vol = volume * ((high - close) / price_range)
                delta = buy_vol - sell_vol
                cvd = delta.cumsum()
                
                latest_delta = float(delta.iloc[-1])
                cvd_change = float(cvd.iloc[-1] - cvd.iloc[-5])

                # 2. GAMMA EXPOSURE (GEX)
                returns = close.pct_change()
                volatility = float(returns.std() * np.sqrt(252))
                price_change_pct = ((current_price - prev_close) / prev_close) * 100
                gamma_exposure = (price_change_pct * volatility) * (float(volume.iloc[-1]) / 100000)

                # 3. VOLUME PROFILE / VPOC
                hist, bin_edges = np.histogram(close, bins=15, weights=volume)
                max_vol_index = np.argmax(hist)
                vpoc_price = (bin_edges[max_vol_index] + bin_edges[max_vol_index + 1]) / 2

                # 4. TECHNICAL INDICATORS (RSI & SMA 20)
                diff = close.diff()
                gain = (diff.where(diff > 0, 0)).rolling(14).mean()
                loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                latest_rsi = float(rsi.iloc[-1])
                sma_20 = float(close.rolling(20).mean().iloc[-1])

                # 5. DECISION ENGINE
                score = 0
                if latest_delta > 0: score += 1.5
                else: score -= 1.5
                if cvd_change > 0: score += 1.0
                else: score -= 1.0
                if gamma_exposure > 0: score += 1.0
                else: score -= 1.0
                if latest_rsi < 35: score += 1.5
                elif latest_rsi > 65: score -= 1.5
                if current_price > sma_20: score += 1.0
                else: score -= 1.0

                currency_symbol = "$" if ("USD" in symbol or "=" in symbol) else "₹"

                # Dashboard Display
                st.subheader(f"📌 Market Overview: {symbol}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Current Price", f"{currency_symbol}{current_price:,.2f}")
                m2.metric("RSI (14)", f"{latest_rsi:.1f}")
                m3.metric("Delta Footprint", f"{latest_delta:,.0f}")
                m4.metric("VPOC Level", f"{currency_symbol}{vpoc_price:,.2f}")

                st.divider()

                # Decision Logic & Risk Calculations
                max_risk_amount = total_capital * (risk_per_trade_pct / 100)

                if score >= 3.0:
                    stop_loss = current_price * 0.98
                    target = current_price * 1.05
                    sl_per_unit = current_price - stop_loss
                    position_units = max_risk_amount / sl_per_unit if sl_per_unit > 0 else 0
                    risk_reward_ratio = (target - current_price) / sl_per_unit if sl_per_unit > 0 else 0

                    st.success("🟢 **TRADERS ANKIT SIGNAL: STRONG BUY (बुलिश सेटअप)**")
                    st.info(f"📍 Entry: {currency_symbol}{current_price:,.2f} | 🛡 SL: {currency_symbol}{stop_loss:,.2f} | 🎯 Target: {currency_symbol}{target:,.2f}")

                    st.markdown("### 🧮 Position Sizing & Risk Breakdown")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Max Allowed Risk", f"{currency_symbol}{max_risk_amount:,.2f} ({risk_per_trade_pct}%)")
                    c2.metric("Position Quantity/Units", f"{position_units:.4f}")
                    c3.metric("Trade Value", f"{currency_symbol}{(position_units * current_price):,.2f}")
                    c4.metric("Risk:Reward", f"1 : {risk_reward_ratio:.1f}")

                    telegram_msg = (
                        f"🚀 *TRADERS ANKIT - LIQUIDITY ALERT* 🚀\n\n"
                        f"🪙 *Asset:* {symbol}\n"
                        f"📈 *Signal:* STRONG BUY 🟢\n"
                        f"💵 *Current Price:* {currency_symbol}{current_price:,.2f}\n"
                        f"📍 *Entry:* {currency_symbol}{current_price:,.2f}\n"
                        f"🛡️ *Stop Loss:* {currency_symbol}{stop_loss:,.2f}\n"
                        f"🎯 *Target:* {currency_symbol}{target:,.2f}\n\n"
                        f"🛡️ *RISK & POSITION SIZING:*\n"
                        f"• Max Risk Amount: {currency_symbol}{max_risk_amount:,.2f}\n"
                        f"• Rec. Quantity: {position_units:.4f} Units\n"
                        f"• Risk-to-Reward: 1:{risk_reward_ratio:.1f}\n\n"
                        f"📊 *Order Flow Info:*\n"
                        f"• Delta: {latest_delta:,.0f} | RSI: {latest_rsi:.1f}"
                    )

                elif score <= -3.0:
                    stop_loss = current_price * 1.02
                    target = current_price * 0.95
                    sl_per_unit = stop_loss - current_price
                    position_units = max_risk_amount / sl_per_unit if sl_per_unit > 0 else 0
                    risk_reward_ratio = (current_price - target) / sl_per_unit if sl_per_unit > 0 else 0

                    st.error("🔴 **TRADERS ANKIT SIGNAL: STRONG SELL (बेयरिश सेटअप)**")
                    st.info(f"📍 Entry: {currency_symbol}{current_price:,.2f} | 🛡️ SL: {currency_symbol}{stop_loss:,.2f} | 🎯 Target: {currency_symbol}{target:,.2f}")

                    st.markdown("### 🧮 Position Sizing & Risk Breakdown")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Max Allowed Risk", f"{currency_symbol}{max_risk_amount:,.2f} ({risk_per_trade_pct}%)")
                    c2.metric("Position Quantity/Units", f"{position_units:.4f}")
                    c3.metric("Trade Value", f"{currency_symbol}{(position_units * current_price):,.2f}")
                    c4.metric("Risk:Reward", f"1 : {risk_reward_ratio:.1f}")

                    telegram_msg = (
                        f"🚨 *TRADERS ANKIT - LIQUIDITY ALERT* 🚨\n\n"
                        f"🪙 *Asset:* {symbol}\n"
                        f"📉 *Signal:* STRONG SELL 🔴\n"
                        f"💵 *Current Price:* {currency_symbol}{current_price:,.2f}\n"
                        f"📍 *Entry:* {currency_symbol}{current_price:,.2f}\n"
                        f"🛡️ *Stop Loss:* {currency_symbol}{stop_loss:,.2f}\n"
                        f"🎯 *Target:* {currency_symbol}{target:,.2f}\n\n"
                        f"🛡️ *RISK & POSITION SIZING:*\n"
                        f"• Max Risk Amount: {currency_symbol}{max_risk_amount:,.2f}\n"
                        f"• Rec. Quantity: {position_units:.4f} Units\n"
                        f"• Risk-to-Reward: 1:{risk_reward_ratio:.1f}\n\n"
                        f"📊 *Order Flow Info:*\n"
                        f"• Delta: {latest_delta:,.0f} | RSI: {latest_rsi:.1f}"
                    )

                else:
                    st.warning("🟡 **TRADERS ANKIT SIGNAL: WAIT / NEUTRAL**")
                    st.write("कोई साफ़ लिक्विडिटी या ब्रेकआउट नहीं है। इंतज़ार करें।")
                    telegram_msg = ""

                # Send Telegram Notification
                if telegram_msg and tg_token and tg_chat_id:
                    if send_telegram_alert(tg_token, tg_chat_id, telegram_msg):
                        st.toast("✅ Telegram पर Risk Breakdown के साथ अलर्ट भेज दिया गया है!", icon="📱")

        except Exception as e:
            st.error(f"एनालिसिस में एरर आया: {e}")
            
