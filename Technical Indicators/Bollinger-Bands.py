import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import os
from ta.volatility import BollingerBands

# Load Alpaca API keys
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")

# Alpaca data client
client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)

# ---------------- PARAMETERS ---------------- #
symbol = "SPY"
bar_count_days = 365
bb_period = 20

# ---------------- TIMEFRAME ---------------- #
end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(days=bar_count_days)
timeframe = TimeFrame.Day

# ---------------- FETCH DATA ---------------- #
params = StockBarsRequest(
    symbol_or_symbols=[symbol],
    timeframe=timeframe,
    start=start_time.isoformat(),
    end=end_time.isoformat(),
    feed="iex",
    limit=1000
)
bars = client.get_stock_bars(params).data.get(symbol)

if not bars:
    print(f"No data returned for {symbol}")
    exit()

# ---------------- DATAFRAME ---------------- #
df = pd.DataFrame([bar.model_dump() for bar in bars])
df['time'] = pd.to_datetime(df['timestamp'])

# ---------------- BOLLINGER BANDS ---------------- #
bb = BollingerBands(close=df['close'], window=bb_period, window_dev=2)
df['bb_mavg'] = bb.bollinger_mavg()
df['bb_upper'] = bb.bollinger_hband()
df['bb_lower'] = bb.bollinger_lband()

# ---------------- SIGNALS ---------------- #
df['buy_signal'] = (df['close'] < df['bb_lower'])
df['sell_signal'] = (df['close'] > df['bb_upper'])

# ---------------- PLOT ---------------- #
plt.figure(figsize=(16, 8))
plt.plot(df['time'], df['close'], label='Close Price', color='blue')
plt.plot(df['time'], df['bb_upper'], label='Upper Band', linestyle='--', color='red')
plt.plot(df['time'], df['bb_lower'], label='Lower Band', linestyle='--', color='green')
plt.plot(df['time'], df['bb_mavg'], label='Middle Band (20 SMA)', color='gray')

plt.fill_between(df['time'], df['bb_lower'], df['bb_upper'],
                 where=~df['bb_upper'].isna(), color='lightgray', alpha=0.3)

# ---------------- SIGNAL ARROWS ---------------- #
# Buy signals
buy_signals = df[df['buy_signal']]
plt.scatter(buy_signals['time'], buy_signals['close'],
            marker='v', color='green', label='Buy Signal', s=100)

# Sell signals
sell_signals = df[df['sell_signal']]
plt.scatter(sell_signals['time'], sell_signals['close'],
            marker='^', color='red', label='Sell Signal', s=100)

# ---------------- FINALIZE PLOT ---------------- #
plt.title(f"{symbol} - 1 Year Daily Bollinger Bands with Buy/Sell Signals")
plt.xlabel("Date")
plt.ylabel("Price ($)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
