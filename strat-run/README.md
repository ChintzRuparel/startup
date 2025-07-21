
# 🧠 High-Frequency Scalping Strategy Using Alpaca API (Python)

This repository implements a **High-Frequency Trading (HFT) scalping strategy** for the US equity market (tested on `SPY`) using real-time data from **Alpaca Markets** and popular **technical indicators** to generate actionable buy/sell signals. It includes:

- 📈 Technical Indicator Analysis  
- ✅ Dynamic Buy/Sell Signal Generation  
- 🚨 Trailing Stop Loss Handling  
- 📧 Email Alerts  
- 🧾 Detailed Audit Logging  

---

## 🧰 Requirements

- Python 3.8+
- Alpaca Account (with API keys)
- Gmail account (for alerts)
- `.env` file with credentials

Install required packages:

```bash
pip install pandas ta python-dotenv alpaca-trade-api pytz
```

---

## 🔐 .env Configuration

Create a `.env` file and include your keys and credentials:

```ini
DATA_KEY=your_alpaca_data_key
DATA_SECRET=your_alpaca_data_secret
TRADE_KEY=your_alpaca_trade_key
TRADE_SECRET=your_alpaca_trade_secret

EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_email_app_password
EMAIL_RECEIVER=receiver_email@gmail.com
```

---

## ⚙️ Strategy Parameters

| Parameter         | Description                                |
|------------------|--------------------------------------------|
| `SYMBOL`         | Stock symbol (e.g. SPY)                    |
| `POSITION_SIZE`  | Number of shares per order (e.g. 10)       |
| `TIMEFRAME`      | Data interval (set to `1 minute`)          |
| `TIMEZONE`       | Market time zone (Eastern US)              |

---

## 📊 Technical Indicators Used

### 📌 1. **Bollinger Bands (BB)**  
- **Window**: 10  
- **Standard Deviation**: 1.5  
- **Purpose**: Detect overbought/oversold levels

```python
bb = BollingerBands(close=df['close'], window=10, window_dev=1.5)
```

### 📌 2. **MACD (Moving Average Convergence Divergence)**  
- **Fast EMA**: 9  
- **Slow EMA**: 21  
- **Signal Line**: 7  
- **Purpose**: Capture trend direction/momentum

```python
macd = MACD(close=df['close'], window_fast=9, window_slow=21, window_sign=7)
```

### 📌 3. **ATR (Average True Range)**  
- **Window**: 5  
- **Purpose**: Measure volatility to confirm trend strength

```python
atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=5)
```

- **Median ATR (50-period)** used as threshold:
```python
atr_median = df['atr'].rolling(window=50).median()
```

### 📌 4. **VWAP (Volume Weighted Average Price)**  
- **Window**: 30  
- **Purpose**: Institutional trading benchmark

```python
vwap = VolumeWeightedAveragePrice(
    high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=30
)
```

---

## 🧠 Buy Conditions (ALL must be TRUE)

| Condition | Explanation |
|----------|-------------|
| `C1` | **Price above VWAP** → Indicates buyer strength. |
| `C2` | **MACD > Signal** → Bullish momentum. |
| `C3` | **Price below Lower Bollinger Band** → Potential bounce. |
| `C4` | **ATR > Median ATR** → Significant volatility (momentum confirmation). |

```python
buy_signal = C1 and C2 and C3 and C4
```

---

## 🧠 Sell Conditions (ALL must be TRUE)

| Condition | Explanation |
|----------|-------------|
| `S1` | **Price below VWAP** → Bearish pressure. |
| `S2` | **MACD < Signal** → Bearish momentum. |
| `S3` | **Price above Upper Bollinger Band** → Mean reversion expected. |
| `S4` | **ATR > Median ATR** → Volatile drop likely. |

```python
sell_signal = S1 and S2 and S3 and S4
```

---

## 🛑 Trailing Stop Loss Mechanism

After a BUY:
- The `highest_price_since_entry` is tracked.
- If price falls more than **1.5%** from the highest recorded level since entry, a **market sell** is triggered.

```python
trailing_stop_trigger = highest_price_since_entry * 0.985
```

This ensures profits are locked in **without waiting** for all sell conditions.

---

## 💸 Trade Execution

Executed via Alpaca Paper Trading API:

```python
order = MarketOrderRequest(
    symbol=SYMBOL,
    qty=POSITION_SIZE,
    side=OrderSide.BUY or SELL,
    time_in_force=TimeInForce.DAY
)
trading_client.submit_order(order)
```

---

## 📬 Email Alerts (via Gmail SMTP)

Upon every BUY, SELL, or STOP execution, an email is sent to notify the user with:

- Trade Type
- Timestamp
- Executed Price
- Quantity

---

## 📑 Audit Logging

Each loop iteration logs:

- Timestamp
- Price
- Indicator values
- All conditions
- Signal flags
- Trade status

All logs are saved to a `.csv` with format:

```bash
strat_SPY_YYYYMMDD_HHMMSS.csv
```

---

## 🔁 Strategy Loop

Runs every 60 seconds:
- Checks if market is open (`9:30 AM - 4:00 PM EST`)
- Pulls 2 hours of 1-minute data
- Computes indicators
- Evaluates signals
- Executes trades if needed
- Applies trailing stop
- Sends emails
- Appends log

---

## 🛑 Exit Condition

If market is **closed**, the loop breaks and saves the final audit log to disk.

---

## 🛠 Error Handling

Any exceptions during runtime are caught and printed, and the audit log is still saved.

---

## 📌 Example Console Output

```
🔍 Conditions Check at 2025-07-21 14:01:00:
  BUY Conditions:
   1) Close > VWAP: True (542.12 > 541.76)
   2) MACD > MACD Signal: True (0.0031 > 0.0028)
   3) Close < BB Lower: True (542.12 < 542.30)
   4) ATR > ATR Median: True (1.231 > 1.129)
  => BUY Signal: True

✅ BUY executed at 2025-07-21 14:01:00 - $542.12
```

---

## ✅ Future Improvements

- Add Stop Limit Orders
- Visual Dashboard via Streamlit
- Slack/Telegram Alerts
- Multisymbol support

---

## Email Preview
<img width="970" height="422" alt="image" src="https://github.com/user-attachments/assets/1b73e9ab-8496-4f7c-83e8-fb45433356c4" />


## 📬 Contact

Made with ❤️ by **[Chintan N Ruparel](mailto:cr3745@nyu.edu)**  
For any bugs or questions, feel free to reach out!
