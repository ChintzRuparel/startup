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

# =============================================
# 🔐 Load credentials
# =============================================
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")

DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")

# =============================================
# 📡 Alpaca Clients
# =============================================
crypto_client = CryptoHistoricalDataClient(DATA_KEY, DATA_SECRET)
trading_client = TradingClient(TRADE_KEY, TRADE_SECRET, paper=True)

# =============================================
# ⚙️ Strategy Settings
# =============================================
SYMBOL = "BTC/USD"
POSITION_SIZE = 0.001
TIMEFRAME = TimeFrame.Minute  # use 1-min bars for crypto

in_position = False
entry_price = None
highest_price = None

print("🚀 Starting continuous BTC time-action scalp bot (TP +0.2%, trailing SL -0.5%)")

while True:
    try:
        utc_now = datetime.now(timezone.utc)
        start = utc_now - timedelta(minutes=5)

        request = CryptoBarsRequest(
            symbol_or_symbols=[SYMBOL],
            timeframe=TIMEFRAME,
            start=start.isoformat(),
            end=utc_now.isoformat()
        )

        bars = crypto_client.get_crypto_bars(request).data.get(SYMBOL)
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
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(order)

            entry_price = current_price
            highest_price = current_price
            in_position = True

            print(f"✅ BUY @ ${entry_price:.2f}")

        else:
            # Update peak
            highest_price = max(highest_price, current_price)

            take_profit = entry_price * 1.002  # +0.2%
            trailing_stop = highest_price * 0.995  # -0.5% from peak

            if current_price >= take_profit:
                order = MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=POSITION_SIZE,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.GTC
                )
                trading_client.submit_order(order)
                print(f"🎯 TAKE PROFIT @ ${current_price:.2f} (Entry: ${entry_price:.2f})")
                in_position = False
                entry_price = None
                highest_price = None

            elif current_price <= trailing_stop:
                order = MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=POSITION_SIZE,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.GTC
                )
                trading_client.submit_order(order)
                print(f"🚨 TRAILING STOP @ ${current_price:.2f} (Peak: ${highest_price:.2f})")
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

    time.sleep(1)  # 🔁 every second
