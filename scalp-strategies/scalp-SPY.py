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
# 📡 Alpaca Clients
# =============================================
stock_client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)
trading_client = TradingClient(TRADE_KEY, TRADE_SECRET, paper=True)

# =============================================
# ⚙️ Strategy Settings
# =============================================
SYMBOL = "SPY"
POSITION_SIZE = 100  # Example: 1 share
TIMEFRAME = TimeFrame.Minute  # Only minute-level for stocks

in_position = False
entry_price = None
highest_price = None

# =============================================
# 📧 Send Email Function
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
# 🔁 Continuous Trading Loop w/ Market Hours
# =============================================

print("🚀 Starting SPY Continuous Time-Action Scalper (TP +0.2% | SL -0.5% | Market Hours Only)")

while True:
    try:
        # 🕒 Check US market open (New York Time)
        ny_time = datetime.now(pytz.timezone("America/New_York"))
        market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = ny_time.replace(hour=16, minute=0, second=0, microsecond=0)

        if ny_time < market_open or ny_time > market_close:
            print(f"⏰ Market closed (NY time: {ny_time.strftime('%Y-%m-%d %H:%M:%S')}). Sleeping for 5 min...")
            time.sleep(300)
            continue

        # === Get latest price ===
        utc_now = datetime.now(timezone.utc)
        start = utc_now - timedelta(minutes=5)

        request = StockBarsRequest(
            symbol_or_symbols=[SYMBOL],
            timeframe=TIMEFRAME,
            start=start.isoformat(),
            end=utc_now.isoformat(),
            feed="iex"
        )

        bars = stock_client.get_stock_bars(request).data.get(SYMBOL)
        if not bars:
            print("⚠️ No bars returned, waiting...")
            time.sleep(1)
            continue

        latest_bar = bars[-1]
        current_price = latest_bar.close

        if not in_position:
            # === BUY ===
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=POSITION_SIZE,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order)

            entry_price = current_price
            highest_price = current_price
            in_position = True

            print(f"✅ BUY @ ${entry_price:.2f}")
            send_trade_email(
                "✅ SPY BUY Executed",
                f"BUY Order\nSymbol: {SYMBOL}\nEntry Price: ${entry_price:.2f}\nQty: {POSITION_SIZE}"
            )

        else:
            highest_price = max(highest_price, current_price)
            take_profit = entry_price * 1.002  # +0.2% TP
            trailing_stop = highest_price * 0.995  # -0.5% SL

            if current_price >= take_profit:
                order = MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=POSITION_SIZE,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                trading_client.submit_order(order)

                print(f"🎯 TAKE PROFIT @ ${current_price:.2f} (Entry: ${entry_price:.2f})")
                send_trade_email(
                    "🎯 SPY TAKE PROFIT",
                    f"TP Hit\nSymbol: {SYMBOL}\nEntry: ${entry_price:.2f}\nExit: ${current_price:.2f}\nQty: {POSITION_SIZE}"
                )

                in_position = False
                entry_price = None
                highest_price = None

            elif current_price <= trailing_stop:
                order = MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=POSITION_SIZE,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                trading_client.submit_order(order)

                print(f"🚨 TRAILING STOP @ ${current_price:.2f} (Peak: ${highest_price:.2f})")
                send_trade_email(
                    "🚨 SPY Trailing Stop SELL",
                    f"SL Hit\nSymbol: {SYMBOL}\nPeak: ${highest_price:.2f}\nExit: ${current_price:.2f}\nQty: {POSITION_SIZE}"
                )

                in_position = False
                entry_price = None
                highest_price = None

            else:
                print(
                    f"⏱️ HOLD | Price: ${current_price:.2f} | Entry: ${entry_price:.2f} "
                    f"| Peak: ${highest_price:.2f} | TP: ${take_profit:.2f} | SL: ${trailing_stop:.2f}"
                )

    except Exception as e:
        print(f"⚠️ ERROR: {e}")

    time.sleep(1)
