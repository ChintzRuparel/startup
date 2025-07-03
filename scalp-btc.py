import os
import time
from datetime import datetime, timezone, timedelta

import pandas as pd
from dotenv import load_dotenv

from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from ta.trend import MACD
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =============================================
# 🔐 Load credentials
# =============================================
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")

DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# =============================================
# 📡 Alpaca crypto clients
# =============================================
crypto_client = CryptoHistoricalDataClient(DATA_KEY, DATA_SECRET)
trading_client = TradingClient(TRADE_KEY, TRADE_SECRET, paper=True)

# =============================================
# ⚙️ Strategy settings
# =============================================
SYMBOL = "BTC/USD"
POSITION_SIZE = 0.001  # Example: 0.001 BTC per trade
TIMEFRAME = TimeFrame.Minute

in_position = False
highest_price_since_entry = None

# =============================================
# 📧 Send email
# =============================================
def send_trade_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_RECEIVER, msg.as_string())

# =============================================
# 🔁 LIVE loop (24/7 for crypto)
# =============================================

print("🚀 Starting LIVE BTC SCALPING STRATEGY with trailing stops & email alerts!")

while True:
    try:
        # Short rolling window for fresh signals
        utc_now = datetime.now(timezone.utc)
        start = utc_now - timedelta(minutes=30)  # tighter window for scalping

        request = CryptoBarsRequest(
            symbol_or_symbols=[SYMBOL],
            timeframe=TIMEFRAME,
            start=start.isoformat(),
            end=utc_now.isoformat()
        )

        bars = crypto_client.get_crypto_bars(request).data.get(SYMBOL)
        if not bars:
            print("⚠️ No crypto bars returned, skipping this loop...")
            time.sleep(30)
            continue

        df = pd.DataFrame([bar.model_dump() for bar in bars])
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)

        # Indicators for scalp logic
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()

        macd = MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()

        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=5)
        df['atr'] = atr.average_true_range()
        atr_median = df['atr'].rolling(window=15).median()

        vwap = VolumeWeightedAveragePrice(
            high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=15
        )
        df['vwap'] = vwap.volume_weighted_average_price()

        latest = df.iloc[-1]

        # 📈 Scalping Buy: price bounces off lower BB, MACD bullish, price > VWAP
        buy_signal = (
            (latest['close'] < latest['bb_lower']) and
            (latest['macd'] > latest['macd_signal']) and
            (latest['close'] > latest['vwap']) and
            (latest['atr'] > atr_median.iloc[-1])
        )

        # 📉 Scalping Sell: price hits upper BB, MACD bearish
        sell_signal = (
            (latest['close'] > latest['bb_upper']) and
            (latest['macd'] < latest['macd_signal'])
        )

        # ✅ BUY
        if buy_signal and not in_position:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=POSITION_SIZE,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(order)
            in_position = True
            highest_price_since_entry = latest['close']

            print(f"✅ BUY @ {latest.name} - ${latest['close']:.2f}")
            send_trade_email(
                f"✅ BTC BUY Executed",
                f"BUY Order\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nQty: {POSITION_SIZE}"
            )

        # ✅ Update high
        if in_position:
            highest_price_since_entry = max(highest_price_since_entry, latest['close'])

        # 🚨 Trailing Stop ~0.5% for scalp
        if in_position and highest_price_since_entry:
            trailing_stop_trigger = highest_price_since_entry * 0.995
            if latest['close'] <= trailing_stop_trigger:
                order = MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=POSITION_SIZE,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.GTC
                )
                trading_client.submit_order(order)
                in_position = False
                highest_price_since_entry = None

                print(f"🚨 TRAILING STOP @ {latest.name} - ${latest['close']:.2f}")
                send_trade_email(
                    f"🚨 BTC Trailing Stop SELL",
                    f"Trailing Stop Triggered\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nTrigger: ${trailing_stop_trigger:.2f}\nQty: {POSITION_SIZE}"
                )

        # ❌ Manual Sell if upper band hit and MACD bearish
        elif sell_signal and in_position:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=POSITION_SIZE,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(order)
            in_position = False
            highest_price_since_entry = None

            print(f"❌ SELL @ {latest.name} - ${latest['close']:.2f}")
            send_trade_email(
                f"❌ BTC SELL Executed",
                f"SELL Order\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nQty: {POSITION_SIZE}"
            )

        else:
            print(f"⏱️ {latest.name} | No Trade | In Position: {in_position} | Price: ${latest['close']:.2f}")

    except Exception as e:
        print(f"⚠️ ERROR: {e}")

    # Next candle
    time.sleep(60)
