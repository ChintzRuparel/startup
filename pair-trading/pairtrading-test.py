import os
import time
from datetime import datetime, timezone, timedelta
import pytz
import pandas as pd
from dotenv import load_dotenv
import traceback

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========== CONFIGURATION ===========
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

data_client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)
trading_client = TradingClient(TRADE_KEY, TRADE_SECRET, paper=True)

SYMBOL_A = "SPY"
SYMBOL_B = "QQQ"
SPREAD_LOOKBACK = 60     # bars for rolling stats
TRADE_DOLLARS = 5000     # $ per leg
Z_ENTER = 2.0            # z-score threshold to enter trade
TARGET_USD = 100         # profit target dollars for pair exit
STOP_USD = -50           # stop loss dollars for pair exit
TIMEFRAME = TimeFrame.Minute
TIMEZONE = pytz.timezone("America/New_York")

# ===== AUDIT LOG SETUP =====
audit_log = []
start_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
audit_filename = f"pair_trading_{SYMBOL_A}_{SYMBOL_B}_{start_timestamp}.csv"

def send_trade_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_RECEIVER, msg.as_string())
    except Exception as e:
        print(f"⚠️ Email sending failed: {e}")

# ============ STRATEGY STATE ============
in_pair_position = False
side_a = None   # 1 = long SPY, -1 = short SPY
side_b = None   # 1 = long QQQ, -1 = short QQQ
entry_a = None
entry_b = None
qty_a = 0
qty_b = 0
pnl_total = 0.0  # initialize to avoid name errors

print("🚀 Starting PAIR-TRADING Scalping Strategy | SPY vs QQQ | SL: $50 | Target: $100")

try:
    while True:
        ny_time = datetime.now(TIMEZONE)
        market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = ny_time.replace(hour=16, minute=0, second=0, microsecond=0)

        if ny_time < market_open:
            print(f"⏰ Market not open yet (NY time: {ny_time.strftime('%Y-%m-%d %H:%M:%S')}). Waiting 5 minutes...")
            time.sleep(300)
            continue

        if ny_time >= market_close:
            print("✅ Market closed. Exiting loop.")
            break

        # Fetch recent data for both symbols: add buffer for extra bars to ensure full window
        utc_now = datetime.now(timezone.utc)
        start = utc_now - timedelta(minutes=SPREAD_LOOKBACK + 20)

        request_a = StockBarsRequest(
            symbol_or_symbols=[SYMBOL_A],
            timeframe=TIMEFRAME,
            start=start.isoformat(),
            end=utc_now.isoformat(),
            feed="iex"
        )
        request_b = StockBarsRequest(
            symbol_or_symbols=[SYMBOL_B],
            timeframe=TIMEFRAME,
            start=start.isoformat(),
            end=utc_now.isoformat(),
            feed="iex"
        )

        bars_a = data_client.get_stock_bars(request_a).data.get(SYMBOL_A)
        bars_b = data_client.get_stock_bars(request_b).data.get(SYMBOL_B)

        print(f"Fetched {len(bars_a) if bars_a else 0} bars for {SYMBOL_A}")
        print(f"Fetched {len(bars_b) if bars_b else 0} bars for {SYMBOL_B}")

        # Check data sufficiency
        if not bars_a or not bars_b or len(bars_a) < SPREAD_LOOKBACK or len(bars_b) < SPREAD_LOOKBACK:
            print(f"⚠️ No/few data returned for {SYMBOL_A} or {SYMBOL_B}. Retrying in 60 seconds...")
            time.sleep(60)
            continue

        # Prepare dataframes, set datetime index, sort
        df_a = pd.DataFrame([bar.model_dump() for bar in bars_a])
        df_a['time'] = pd.to_datetime(df_a['timestamp'])
        df_a.set_index('time', inplace=True)
        df_a.sort_index(inplace=True)

        df_b = pd.DataFrame([bar.model_dump() for bar in bars_b])
        df_b['time'] = pd.to_datetime(df_b['timestamp'])
        df_b.set_index('time', inplace=True)
        df_b.sort_index(inplace=True)

        # Merge on overlapping timestamps
        df = pd.DataFrame({
            'close_a': df_a['close'],
            'close_b': df_b['close']
        }).dropna()

        # Calculate spread and rolling statistics
        spread = df['close_a'] - df['close_b']
        spread_mean = spread.rolling(window=SPREAD_LOOKBACK).mean()
        spread_std = spread.rolling(window=SPREAD_LOOKBACK).std()
        z_score = (spread - spread_mean) / spread_std

        latest = df.iloc[-1]
        latest_z = z_score.iloc[-1]
        prev_z = z_score.iloc[-2] if len(z_score) > 1 else 0.0
        latest_time = df.index[-1]
        close_a = latest['close_a']
        close_b = latest['close_b']

        # Skip iteration if z-score NaN
        if pd.isna(latest_z) or pd.isna(prev_z):
            print(f"⚠️ Z-score not available at {latest_time}. Skipping iteration.")
            time.sleep(60)
            continue

        # Calculate order quantities ensuring minimum 1 share
        qty_a = max(int(TRADE_DOLLARS / close_a), 1)
        qty_b = max(int(TRADE_DOLLARS / close_b), 1)

        # Calculate current PnL if in position
        if in_pair_position:
            pnl_a = (close_a - entry_a) * qty_a * side_a
            pnl_b = (close_b - entry_b) * qty_b * side_b
            pnl_total = pnl_a + pnl_b
        else:
            pnl_total = 0.0

        # ENTRY LOGIC
        if not in_pair_position and abs(latest_z) > Z_ENTER:
            if latest_z > Z_ENTER:
                side_a, side_b = -1, 1  # Short A, Long B
            else:
                side_a, side_b = 1, -1  # Long A, Short B

            try:
                print(f"Attempting entry orders: {SYMBOL_A} {'BUY' if side_a == 1 else 'SELL'}, {SYMBOL_B} {'BUY' if side_b == 1 else 'SELL'}")
                trading_client.submit_order(MarketOrderRequest(
                    symbol=SYMBOL_A,
                    qty=qty_a,
                    side=OrderSide.BUY if side_a == 1 else OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                ))
                trading_client.submit_order(MarketOrderRequest(
                    symbol=SYMBOL_B,
                    qty=qty_b,
                    side=OrderSide.BUY if side_b == 1 else OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                ))

                entry_a = close_a
                entry_b = close_b
                in_pair_position = True
                pnl_total = 0.0

                print(f"✅ PAIR TRADE ENTERED: {SYMBOL_A} {'LONG' if side_a == 1 else 'SHORT'} @{entry_a:.2f} | "
                      f"{SYMBOL_B} {'LONG' if side_b == 1 else 'SHORT'} @{entry_b:.2f}")

                send_trade_email(
                    f"✅ Pair Trade Open: {SYMBOL_A}/{SYMBOL_B}",
                    f"PAIR TRADE ENTRY\nTime: {latest_time}\n"
                    f"{SYMBOL_A}: {'LONG' if side_a == 1 else 'SHORT'} {qty_a} @ {entry_a:.2f}\n"
                    f"{SYMBOL_B}: {'LONG' if side_b == 1 else 'SHORT'} {qty_b} @ {entry_b:.2f}\n"
                )

            except Exception as e:
                print(f"⚠️ Order submission failed on entry: {e}")
                traceback.print_exc()
                # Reset variables on failure
                entry_a = entry_b = None
                side_a = side_b = None

        # EXIT LOGIC
        elif in_pair_position:
            do_exit = False
            reason = ""

            if pnl_total >= TARGET_USD:
                do_exit = True
                reason = f"TARGET hit (${pnl_total:.2f} >= ${TARGET_USD})"
            elif pnl_total <= STOP_USD:
                do_exit = True
                reason = f"STOP hit (${pnl_total:.2f} <= ${STOP_USD})"
            elif prev_z * latest_z < 0:  # Z-score crossing zero mean reversion
                do_exit = True
                reason = f"REVERSION detected (z-score {prev_z:.2f} -> {latest_z:.2f})"

            if do_exit:
                try:
                    print(f"Attempting exit orders due to {reason}")
                    trading_client.submit_order(MarketOrderRequest(
                        symbol=SYMBOL_A,
                        qty=qty_a,
                        side=OrderSide.SELL if side_a == 1 else OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    ))
                    trading_client.submit_order(MarketOrderRequest(
                        symbol=SYMBOL_B,
                        qty=qty_b,
                        side=OrderSide.SELL if side_b == 1 else OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    ))

                    print(f"❌ PAIR TRADE EXIT ({reason}): {SYMBOL_A} {'LONG' if side_a == 1 else 'SHORT'} @ {close_a:.2f}, "
                          f"{SYMBOL_B} {'LONG' if side_b == 1 else 'SHORT'} @ {close_b:.2f}. "
                          f"PnL: ${pnl_total:.2f}")

                    send_trade_email(
                        f"❌ Pair Trade Exit: {SYMBOL_A}/{SYMBOL_B}",
                        f"PAIR TRADE EXIT\nTime: {latest_time}\n"
                        f"{SYMBOL_A}: Exit @ {close_a:.2f} | PnL: ${pnl_a:.2f}\n"
                        f"{SYMBOL_B}: Exit @ {close_b:.2f} | PnL: ${pnl_b:.2f}\n"
                        f"Total PnL: ${pnl_total:.2f} | Reason: {reason}"
                    )

                    # Reset all positions and states
                    in_pair_position = False
                    side_a = side_b = None
                    entry_a = entry_b = None
                    qty_a = qty_b = 0
                    pnl_total = 0.0

                except Exception as e:
                    print(f"⚠️ Order submission failed on exit: {e}")
                    traceback.print_exc()
            else:
                print(f"⏱ Holding Pair | Z-score: {latest_z:.2f} | PnL: ${pnl_total:.2f}")

        else:
            print(f"⏱️ No open pair trade at {latest_time} | Z-score: {latest_z:.2f}")

        # === Audit Log Update ===
        audit_log.append({
            "timestamp": latest_time,
            "close_spy": close_a,
            "close_qqq": close_b,
            "spread": float(spread.iloc[-1]),
            "z_score": float(latest_z),
            "in_pair_position": in_pair_position,
            "side_a": side_a if side_a is not None else "",
            "side_b": side_b if side_b is not None else "",
            "entry_a": entry_a if entry_a is not None else "",
            "entry_b": entry_b if entry_b is not None else "",
            "qty_a": qty_a,
            "qty_b": qty_b,
            "pnl_total": pnl_total if in_pair_position else "",
        })

        time.sleep(60)

except Exception as e:
    print(f"⚠️ ERROR: {e}")
    traceback.print_exc()

finally:
    audit_df = pd.DataFrame(audit_log)
    audit_df.to_csv(audit_filename, index=False)
    print(f"📑 Final audit log saved to {audit_filename}")
