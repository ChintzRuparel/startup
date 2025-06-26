import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import os
from ta.trend import MACD

# Load Alpaca API keys
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")

# Alpaca client setup
client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)

# Parameters
symbol = "SPY"
days = 365

# Timeframe
end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(days=days)
timeframe = TimeFrame.Day

# Fetch OHLCV
request = StockBarsRequest(
    symbol_or_symbols=[symbol],
    timeframe=timeframe,
    start=start_time.isoformat(),
    end=end_time.isoformat(),
    feed="iex",
    limit=1000
)
bars = client.get_stock_bars(request).data.get(symbol)

if not bars:
    print(f"No data returned for {symbol}")
    exit()

# DataFrame
df = pd.DataFrame([bar.model_dump() for bar in bars])
df['time'] = pd.to_datetime(df['timestamp'])

# MACD calculation
macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
df['macd'] = macd.macd()
df['signal'] = macd.macd_signal()
df['histogram'] = df['macd'] - df['signal']

# Buy/sell signals
df['buy_signal'] = (df['macd'] > df['signal']) & (df['macd'].shift(1) < df['signal'].shift(1))
df['sell_signal'] = (df['macd'] < df['signal']) & (df['macd'].shift(1) > df['signal'].shift(1))

# Plot with TradingView style layout
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})

# --------- Price Chart with Signals --------- #
ax1.plot(df['time'], df['close'], label='Close Price', color='blue')
ax1.scatter(df[df['buy_signal']]['time'], df[df['buy_signal']]['close'], marker='^', color='green', label='Buy Signal', s=100)
ax1.scatter(df[df['sell_signal']]['time'], df[df['sell_signal']]['close'], marker='v', color='red', label='Sell Signal', s=100)
ax1.set_title(f"{symbol} - Price with MACD Buy/Sell Signals")
ax1.set_ylabel("Price ($)")
ax1.grid(True)
ax1.legend()

# --------- MACD Indicator Subplot --------- #
ax2.bar(df['time'], df['histogram'], label='MACD Histogram', color=['green' if val >= 0 else 'red' for val in df['histogram']])
ax2.plot(df['time'], df['macd'], label='MACD Line', color='purple')
ax2.plot(df['time'], df['signal'], label='Signal Line', color='orange')
ax2.axhline(0, linestyle='--', color='gray', linewidth=1)
ax2.set_title("MACD Indicator")
ax2.set_ylabel("MACD")
ax2.set_xlabel("Date")
ax2.grid(True)
ax2.legend()

plt.tight_layout()
plt.show()
