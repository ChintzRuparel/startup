import os
import time
from datetime import datetime, timezone, timedelta
import pytz
import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
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
# ALPACA API KEYS
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")

#GMAIL API KEYS
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# =============================================
# 📡 Alpaca clients
# =============================================
data_client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)
trading_client = TradingClient(TRADE_KEY, TRADE_SECRET, paper=True)

# =============================================
# ⚙️ Strategy settings
# =============================================
SYMBOL = "QQQ"
POSITION_SIZE = 25
TIMEFRAME = TimeFrame.Minute
TIMEZONE = pytz.timezone("America/New_York")

in_position = False
highest_price_since_entry = None
entry_price = None

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
# 🔁 LIVE loop
# =============================================


print("🚀 Starting LIVE HFT STRATEGY with trailing stops & email alerts!")



while True:


    try:

                # 🕒 Check if US market is open
        ny_time = datetime.now(pytz.timezone("America/New_York"))
        market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = ny_time.replace(hour=16, minute=0, second=0, microsecond=0)

        if ny_time < market_open or ny_time > market_close:
            print(f"⏰ Market is closed (NY time: {ny_time}). Waiting for next session...")
            time.sleep(300)  # Sleep for 5 minutes before checking again
            continue

        # ============================
        # 📈 Continue with your normal logic here!

        
        # 2hr rolling window
        utc_now = datetime.now(timezone.utc)
        start = utc_now - timedelta(minutes=120)

        request = StockBarsRequest(
            symbol_or_symbols=[SYMBOL],
            timeframe=TIMEFRAME,
            start=start.isoformat(),
            end=utc_now.isoformat(),
            feed="iex"
        )

        bars = data_client.get_stock_bars(request).data.get(SYMBOL)
        df = pd.DataFrame([bar.model_dump() for bar in bars])
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)

        # Indicators
        bb = BollingerBands(close=df['close'], window=10, window_dev=1.5)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()

        macd = MACD(close=df['close'], window_fast=9, window_slow=21, window_sign=7)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()

        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=5)
        df['atr'] = atr.average_true_range()
        atr_median = df['atr'].rolling(window=50).median()

        vwap = VolumeWeightedAveragePrice(
            high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=30
        )
        df['vwap'] = vwap.volume_weighted_average_price()

        latest = df.iloc[-1]

        buy_signal = (
            (latest['close'] > latest['vwap']) and
            (latest['macd'] > latest['macd_signal']) and
            (latest['close'] < latest['bb_lower']) and
            (latest['atr'] > atr_median.iloc[-1])
        )

        sell_signal = (
            (latest['close'] < latest['vwap']) and
            (latest['macd'] < latest['macd_signal']) and
            (latest['close'] > latest['bb_upper']) and
            (latest['atr'] > atr_median.iloc[-1])
        )

        # ✅ BUY
        if buy_signal and not in_position:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=POSITION_SIZE,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order)
            in_position = True
            entry_price = latest['close']
            highest_price_since_entry = latest['close']

            print(f"✅ BUY at {latest.name} - ${latest['close']:.2f}")
            send_trade_email(
                f"✅ BUY Executed: {SYMBOL}",
                f"BUY Order\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nQty: {POSITION_SIZE}"
            )

        # Update highest
        if in_position:
            highest_price_since_entry = max(highest_price_since_entry, latest['close'])

        # 🚨 Trailing Stop: 1.5%
        trailing_stop_trigger = highest_price_since_entry * 0.985
        if in_position and latest['close'] <= trailing_stop_trigger:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=POSITION_SIZE,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order)
            in_position = False
            entry_price = None
            highest_price_since_entry = None

            print(f"🚨 TRAILING STOP at {latest.name} - ${latest['close']:.2f}")
            send_trade_email(
                f"🚨 Trailing Stop SELL: {SYMBOL}",
                f"Trailing Stop Triggered\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nTrigger: ${trailing_stop_trigger:.2f}\nQty: {POSITION_SIZE}"
            )

        # ❌ SELL signal
        elif sell_signal and in_position:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=POSITION_SIZE,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order)
            in_position = False
            entry_price = None
            highest_price_since_entry = None

            print(f"❌ SELL signal at {latest.name} - ${latest['close']:.2f}")
            send_trade_email(
                f"❌ SELL Executed: {SYMBOL}",
                f"SELL Order\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nQty: {POSITION_SIZE}"
            )
        else:
            print(f"⏱️ No trade at {latest.name} | In Position: {in_position}")

    except Exception as e:
        print(f"⚠️ ERROR: {e}")

    # Wait for next bar
    time.sleep(60)
