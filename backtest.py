import pandas as pd
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import MACD
from ta.volume import VolumeWeightedAveragePrice

# ============ Load Alpaca API ============ #
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")
client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)

# ============ Parameters ============ #
symbol = "QQQ"
timeframe = TimeFrame.Minute
end = datetime(2025, 6, 25, 16, 0, tzinfo=timezone.utc)
start = end - timedelta(days=30)

# ============ Fetch Historical Data ============ #
request = StockBarsRequest(
    symbol_or_symbols=[symbol],
    timeframe=timeframe,
    start=start.isoformat(),
    end=end.isoformat(),
    feed="iex",
    limit=50000
)

bars = client.get_stock_bars(request).data.get(symbol)
if not bars:
    print("No data returned.")
    exit()

df = pd.DataFrame([bar.model_dump() for bar in bars])
df['time'] = pd.to_datetime(df['timestamp'])
df.set_index('time', inplace=True)

# ============ Indicators ============ #
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

# ============ Signal Logic ============ #
df['Buy_signal'] = (
    (df['close'] > df['vwap']) &
    (df['macd'] > df['macd_signal']) &
    (df['close'] < df['bb_lower']) &
    (df['atr'] > atr_median)
)

df['Sell_signal'] = (
    (df['close'] < df['vwap']) &
    (df['macd'] < df['macd_signal']) &
    (df['close'] > df['bb_upper']) &
    (df['atr'] > atr_median)
)

# ============ Backtest ============ #
in_position = False
entry_price = 0
trades = []

for i in range(len(df)):
    if df.iloc[i]['Buy_signal'] and not in_position:
        entry_time = df.index[i]
        entry_price = df.iloc[i]['close']
        in_position = True
    elif df.iloc[i]['Sell_signal'] and in_position:
        exit_time = df.index[i]
        exit_price = df.iloc[i]['close']
        pnl = (exit_price - entry_price) * 100
        trades.append({
            "Entry Time": entry_time,
            "Exit Time": exit_time,
            "Entry Price": entry_price,
            "Exit Price": exit_price,
            "PnL ($)": round(pnl, 2),
            "Return (%)": round(((exit_price - entry_price) / entry_price) * 100, 2)
        })
        in_position = False

# ============ Results ============ #
results_df = pd.DataFrame(trades)

if results_df.empty:
    print("\n⚠️  No trades executed. Try adjusting thresholds or timeframe.")
else:
    total_pnl = results_df["PnL ($)"].sum()
    avg_return = results_df["Return (%)"].mean()
    win_rate = (results_df["PnL ($)"] > 0).sum() / len(results_df) * 100

    print("\n⚡ HFT Strategy Results on QQQ (2025, 1-min)")
    print(results_df.to_string(index=False))
    print(f"\n📈 Total Trades: {len(results_df)}")
    print(f"💰 Total PnL: ${total_pnl:.2f}")
    print(f"📊 Avg Return per Trade: {avg_return:.2f}%")
    print(f"✅ Win Rate: {win_rate:.2f}%")


