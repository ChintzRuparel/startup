import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import os
from ta.volatility import BollingerBands
from ta.trend import MACD
from ta.momentum import RSIIndicator

# -------- Load API keys -------- #
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")

# -------- Alpaca client -------- #
client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)

# -------- Parameters -------- #
symbol = "SPY"
days = 365

# -------- Timeframe -------- #
end = datetime.now(timezone.utc)
start = end - timedelta(days=days)
timeframe = TimeFrame.Day

# -------- Fetch Data -------- #
request = StockBarsRequest(
    symbol_or_symbols=[symbol],
    timeframe=timeframe,
    start=start.isoformat(),
    end=end.isoformat(),
    feed="iex",
    limit=1000
)
bars = client.get_stock_bars(request).data.get(symbol)
if not bars:
    print(f"No data returned for {symbol}")
    exit()

# -------- Data Processing -------- #
df = pd.DataFrame([bar.model_dump() for bar in bars])
df['time'] = pd.to_datetime(df['timestamp'])

# -------- Bollinger Bands -------- #
bb = BollingerBands(close=df['close'], window=20, window_dev=2)
df['bb_mavg'] = bb.bollinger_mavg()
df['bb_upper'] = bb.bollinger_hband()
df['bb_lower'] = bb.bollinger_lband()

# Buy/Sell signals from Bollinger Band
df['bb_buy'] = df['close'] < df['bb_lower']
df['bb_sell'] = df['close'] > df['bb_upper']

# -------- MACD -------- #
macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
df['macd'] = macd.macd()
df['macd_signal'] = macd.macd_signal()
df['macd_hist'] = df['macd'] - df['macd_signal']

# MACD cross signals
df['macd_buy'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) < df['macd_signal'].shift(1))
df['macd_sell'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) > df['macd_signal'].shift(1))

# -------- RSI -------- #
rsi = RSIIndicator(close=df['close'], window=14)
df['rsi'] = rsi.rsi()

# -------- PLOTTING -------- #
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios': [3, 1.5, 1]})

# --- Price + Bollinger --- #
ax1.plot(df['time'], df['close'], label='Close Price', color='blue')
ax1.plot(df['time'], df['bb_upper'], linestyle='--', color='red', label='Upper BB')
ax1.plot(df['time'], df['bb_lower'], linestyle='--', color='green', label='Lower BB')
ax1.plot(df['time'], df['bb_mavg'], linestyle='-', color='gray', label='Middle BB')

# Buy/sell signal markers (Bollinger)
ax1.scatter(df[df['bb_buy']]['time'], df[df['bb_buy']]['close'], marker='^', color='green', s=100, label='BB Buy')
ax1.scatter(df[df['bb_sell']]['time'], df[df['bb_sell']]['close'], marker='v', color='red', s=100, label='BB Sell')

ax1.fill_between(df['time'], df['bb_lower'], df['bb_upper'],
                 where=~df['bb_upper'].isna(), color='lightgray', alpha=0.2)

ax1.set_title(f"{symbol} - Bollinger Bands, MACD, RSI (1 Year Daily)")
ax1.set_ylabel("Price ($)")
ax1.grid(True)
ax1.legend(loc='upper left')

# --- MACD Panel --- #
ax2.bar(df['time'], df['macd_hist'], color=['green' if v >= 0 else 'red' for v in df['macd_hist']], label='MACD Histogram')
ax2.plot(df['time'], df['macd'], color='purple', label='MACD Line')
ax2.plot(df['time'], df['macd_signal'], color='orange', label='Signal Line')
ax2.axhline(0, linestyle='--', color='gray', linewidth=1)

# Buy/Sell signal markers (MACD)
ax2.scatter(df[df['macd_buy']]['time'], df[df['macd_buy']]['macd'], marker='^', color='green', s=70, label='MACD Buy')
ax2.scatter(df[df['macd_sell']]['time'], df[df['macd_sell']]['macd'], marker='v', color='red', s=70, label='MACD Sell')

ax2.set_ylabel("MACD")
ax2.grid(True)
ax2.legend(loc='upper left')

# --- RSI Panel --- #
ax3.plot(df['time'], df['rsi'], label='RSI (14)', color='blue')
ax3.axhline(70, linestyle='--', color='red', label='Overbought (70)')
ax3.axhline(30, linestyle='--', color='green', label='Oversold (30)')
ax3.set_ylabel("RSI")
ax3.set_xlabel("Date")
ax3.grid(True)
ax3.legend(loc='upper left')

plt.tight_layout()
plt.show()
