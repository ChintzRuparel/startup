import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import os
from ta.momentum import RSIIndicator

# Load .env for Alpaca API keys
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")

# Initialize Alpaca historical data client
data_client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)

# ------------------- PARAMETERS ------------------- #
symbol = "SPY"
granularity = "hour"  # Options: "minute", "hour", "day"
rsi_period = 14
bars_to_fetch = 500

# ------------------ TIMEFRAME CONFIG -------------- #
end_time = datetime.now(timezone.utc)

if granularity == "minute":
    timeframe = TimeFrame.Minute
    start_time = end_time - timedelta(minutes=bars_to_fetch)
elif granularity == "hour":
    timeframe = TimeFrame.Hour
    start_time = end_time - timedelta(hours=bars_to_fetch)
elif granularity == "day":
    timeframe = TimeFrame.Day
    start_time = end_time - timedelta(days=bars_to_fetch)
else:
    raise ValueError("Invalid granularity: use 'minute', 'hour', or 'day'")

# ------------------ FETCH OHLCV ------------------- #
request_params = StockBarsRequest(
    symbol_or_symbols=[symbol],
    timeframe=timeframe,
    start=start_time.isoformat(),
    end=end_time.isoformat(),
    feed="iex",
    limit=bars_to_fetch
)

bars = data_client.get_stock_bars(request_params)
bars_data = bars.data.get(symbol)

if not bars_data:
    print(f"No data returned for {symbol}")
    exit()

# ------------------ PROCESS & COMPUTE RSI ------------------- #
df = pd.DataFrame([bar.model_dump() for bar in bars_data])
df['time'] = pd.to_datetime(df['timestamp'])

rsi = RSIIndicator(close=df['close'], window=rsi_period)
df['RSI'] = rsi.rsi()

# ------------------ ALERT SYSTEM ------------------- #
latest_rsi = df['RSI'].iloc[-1]
print(f"Latest RSI for {symbol} ({granularity}): {latest_rsi:.2f}")

if latest_rsi > 70:
    print("📈 ALERT: RSI crossed above 70 (Overbought)")
elif latest_rsi < 30:
    print("📉 ALERT: RSI dropped below 30 (Oversold)")
else:
    print("✅ RSI is in neutral range")

# ------------------ PLOTTING ------------------- #
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# Price chart
ax1.plot(df['time'], df['close'], label='Close Price', color='blue')
ax1.set_title(f"{symbol} Price Chart ({granularity.capitalize()})")
ax1.set_ylabel("Price ($)")
ax1.grid(True)
ax1.legend()

# RSI chart
ax2.plot(df['time'], df['RSI'], label='RSI (14)', color='purple')
ax2.axhline(70, linestyle='--', color='red', label='Overbought (70)')
ax2.axhline(30, linestyle='--', color='green', label='Oversold (30)')
ax2.set_title("Relative Strength Index (RSI)")
ax2.set_ylabel("RSI Value")
ax2.set_xlabel("Time")
ax2.grid(True)
ax2.legend()

plt.tight_layout()
plt.show()
