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

DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")
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
# 📧 Email helper
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
# 🔁 LIVE HFT Loop
# =============================================
print("🚀 Starting LIVE HFT Scalping Strategy with Trailing Stops & Condition Logging")

while True:
    try:
        ny_time = datetime.now(TIMEZONE)
        market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = ny_time.replace(hour=16, minute=0, microsecond=0)

        if ny_time < market_open or ny_time > market_close:
            print(f"⏰ Market closed (NY time: {ny_time.strftime('%Y-%m-%d %H:%M:%S')}). Waiting...")
            time.sleep(300)
            continue

        # 📈 Fetch market data
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
        if not bars or len(bars) == 0:
            print(f"⚠️ No data returned for {SYMBOL}. Retrying in 60 seconds...")
            time.sleep(60)
            continue

        df = pd.DataFrame([bar.model_dump() for bar in bars])
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)

        # 🧮 Indicators
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

        # ✅ Signal conditions
        buy_condition_1 = latest['close'] > latest['vwap']
        buy_condition_2 = latest['macd'] > latest['macd_signal']
        buy_condition_3 = latest['close'] < latest['bb_lower']
        buy_condition_4 = latest['atr'] > atr_median.iloc[-1]
        buy_signal = buy_condition_1 and buy_condition_2 and buy_condition_3 and buy_condition_4

        sell_condition_1 = latest['close'] < latest['vwap']
        sell_condition_2 = latest['macd'] < latest['macd_signal']
        sell_condition_3 = latest['close'] > latest['bb_upper']
        sell_condition_4 = latest['atr'] > atr_median.iloc[-1]
        sell_signal = sell_condition_1 and sell_condition_2 and sell_condition_3 and sell_condition_4

        # ✅ Log condition breakdown
        print(f"\n🔍 Conditions Check at {latest.name}:")
        print(f"  BUY Conditions:")
        print(f"   1) Close > VWAP: {buy_condition_1} ({latest['close']:.2f} > {latest['vwap']:.2f})")
        print(f"   2) MACD > MACD Signal: {buy_condition_2} ({latest['macd']:.4f} > {latest['macd_signal']:.4f})")
        print(f"   3) Close < BB Lower: {buy_condition_3} ({latest['close']:.2f} < {latest['bb_lower']:.2f})")
        print(f"   4) ATR > ATR Median: {buy_condition_4} ({latest['atr']:.4f} > {atr_median.iloc[-1]:.4f})")
        print(f"  => BUY Signal: {buy_signal}")

        print(f"  SELL Conditions:")
        print(f"   1) Close < VWAP: {sell_condition_1} ({latest['close']:.2f} < {latest['vwap']:.2f})")
        print(f"   2) MACD < MACD Signal: {sell_condition_2} ({latest['macd']:.4f} < {latest['macd_signal']:.4f})")
        print(f"   3) Close > BB Upper: {sell_condition_3} ({latest['close']:.2f} > {latest['bb_upper']:.2f})")
        print(f"   4) ATR > ATR Median: {sell_condition_4} ({latest['atr']:.4f} > {atr_median.iloc[-1]:.4f})")
        print(f"  => SELL Signal: {sell_signal}\n")

        # ✅ BUY order
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

            print(
                f"✅ BUY executed at {latest.name} - ${latest['close']:.2f}\n"
                f"   VWAP: {latest['vwap']:.2f}, MACD: {latest['macd']:.4f}, MACD_Signal: {latest['macd_signal']:.4f}\n"
                f"   BB Lower: {latest['bb_lower']:.2f}, ATR: {latest['atr']:.4f}, ATR Median: {atr_median.iloc[-1]:.4f}"
            )

            send_trade_email(
                f"✅ BUY Executed: {SYMBOL}",
                f"BUY Order\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nQty: {POSITION_SIZE}\n\n"
                f"BUY Conditions:\n"
                f"Close > VWAP: {buy_condition_1}\nMACD > MACD_Signal: {buy_condition_2}\n"
                f"Close < BB Lower: {buy_condition_3}\nATR > ATR Median: {buy_condition_4}\n"
                f"VWAP: {latest['vwap']:.2f}\nMACD: {latest['macd']:.4f} | MACD_Signal: {latest['macd_signal']:.4f}\n"
                f"BB Lower: {latest['bb_lower']:.2f}\nATR: {latest['atr']:.4f} | ATR Median: {atr_median.iloc[-1]:.4f}"
            )

        # ✅ Manage open position
        if in_position:
            highest_price_since_entry = max(highest_price_since_entry, latest['close'])
            trailing_stop_trigger = highest_price_since_entry * 0.985

            if latest['close'] <= trailing_stop_trigger:
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

                print(
                    f"🚨 TRAILING STOP triggered at {latest.name} - ${latest['close']:.2f}\n"
                    f"   Highest Price: ${highest_price_since_entry:.2f}\n"
                    f"   Trigger: ${trailing_stop_trigger:.2f}\n"
                )

                send_trade_email(
                    f"🚨 Trailing Stop SELL: {SYMBOL}",
                    f"Trailing Stop Triggered\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nTrigger: ${trailing_stop_trigger:.2f}\nQty: {POSITION_SIZE}"
                )

            elif sell_signal:
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

                print(
                    f"❌ SELL signal executed at {latest.name} - ${latest['close']:.2f}\n"
                )

                send_trade_email(
                    f"❌ SELL Executed: {SYMBOL}",
                    f"SELL Order\nTime: {latest.name}\nPrice: ${latest['close']:.2f}\nQty: {POSITION_SIZE}\n\n"
                    f"SELL Conditions:\n"
                    f"Close < VWAP: {sell_condition_1}\nMACD < MACD_Signal: {sell_condition_2}\n"
                    f"Close > BB Upper: {sell_condition_3}\nATR > ATR Median: {sell_condition_4}\n"
                )

            else:
                print(
                    f"⏱️ Holding | Price: ${latest['close']:.2f} | Highest: ${highest_price_since_entry:.2f} | Trailing Stop: ${trailing_stop_trigger:.2f}\n"
                )

        elif not in_position:
            print(
                f"⏱️ No trade at {latest.name} | In Position: {in_position}"
            )

    except Exception as e:
        print(f"⚠️ ERROR: {e}")

    time.sleep(60)
