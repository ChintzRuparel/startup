
# 📉 Basic SPY Scalper Bot

This is a simple Python script that runs a minute-level P&L-based scalping strategy using Alpaca's API.

It buys SPY when the market opens, and either takes profit or cuts losses based on defined USD thresholds. It also sends email alerts when trades are executed.

---

## 🛠 Requirements

- Python 3.7+
- Alpaca API keys (Data & Trading)
- Gmail credentials for sending email alerts
- `.env` file with credentials

---

## ⚙️ Strategy Details

- **Symbol:** SPY
- **Position Size:** 100 shares
- **Timeframe:** 1-minute
- **Take Profit:** $110
- **Stop Loss:** -$50
- Sends email notifications for each trade
- Operates only during NYSE market hours

---

## 📂 .env Variables

```bash
DATA_KEY=your_data_key
DATA_SECRET=your_data_secret
TRADE_KEY=your_trade_key
TRADE_SECRET=your_trade_secret
EMAIL_USER=you@gmail.com
EMAIL_PASSWORD=yourpassword
EMAIL_RECEIVER=target@gmail.com
```

---

## 🚀 How It Works

1. Waits for market to open
2. Buys SPY once
3. Tracks unrealized P&L
4. Sells either at take profit or stop loss
5. Sends email about the trade
6. Repeats...

---

## 📦 Libraries Used

- `alpaca-trade-api`
- `pandas`
- `pytz`
- `dotenv`
- `smtplib`, `email`

---

## 🧪 Notes

- This is a demo and uses `paper=True` mode.
- Should be run on a cloud server or your local machine with proper error handling.
- Email delivery depends on correct Gmail setup.

---
## Email Preview

<img width="1068" height="420" alt="image" src="https://github.com/user-attachments/assets/a290c6f1-bae1-4ca9-8bcc-c32575e5751a" />

