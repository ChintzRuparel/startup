# SPY/QQQ Pair Trading Scalping Bot

This project implements a **real-time pair trading strategy** between SPY (S&P 500 ETF) and QQQ (NASDAQ 100 ETF) using the Alpaca API in Python. The bot uses statistical arbitrage to scalp short-term mean reversion opportunities while maintaining a market-neutral exposure.

---

## 🧠 Strategy Logic

### Pair Trading with Z-Score

- **Spread Calculation:** The spread is the difference between SPY and QQQ closing prices.
- **Rolling Z-Score:** A moving average and standard deviation of the spread (default: 60 minutes) are used to compute a z-score.
    - **Z = (Spread - Mean) / Std**
- **Entry:**
    - Enter the pair when the z-score exceeds +2 or falls below –2:
        - **Z > +2:** Short SPY, Long QQQ (expecting spread to narrow)
        - **Z < –2:** Long SPY, Short QQQ (expecting spread to widen)
- **Exit:**
    - Close both positions when:
        - **Combined PnL ≥ $100** (profit target)
        - **Combined PnL ≤ -$50** (stop loss)
        - **Or:** Spread mean reverts (z-score crosses zero)
- **Position Sizing:** Each leg is sized for approx. $5,000, ensuring dollar neutrality.
- **Email Alerts:** All trades entries and exits send an email notification.

---

## 🚀 Getting Started

1. **Clone this repository & Install dependencies:**  
    ```
    git clone <your-repo-url>
    cd <repo-folder>
    pip install -r requirements.txt
    ```

2. **Create a `.env` file** (in the repo root) with your API keys and email credentials:
    ```
    DATA_KEY=your_alpaca_data_key
    DATA_SECRET=your_alpaca_data_secret
    TRADE_KEY=your_alpaca_trade_key
    TRADE_SECRET=your_alpaca_trade_secret
    EMAIL_USER=your_gmail_email
    EMAIL_PASSWORD=your_gmail_app_password
    EMAIL_RECEIVER=email_to_receive_alerts
    ```

3. **Run the Bot:**  
    ```
    python pair_trade_spy_qqq.py
    ```

4. **Audit Log:**  
    - All trades and signals are saved to a CSV log file in the script's directory.

---

## ⚙️ Configuration

You can adjust the following parameters in the Python script:

| Variable           | Meaning                         | Default |
|--------------------|---------------------------------|---------|
| SPREAD_LOOKBACK    | Rolling window for z-score      | 60      |
| TRADE_DOLLARS      | Per-leg dollar exposure         | $5000   |
| Z_ENTER            | Z-score entry threshold         | ±2      |
| TARGET_USD         | Combined pair profit target     | $100    |
| STOP_USD           | Combined pair stop loss         | -$50    |

---

## 📑 Example Audit Log

| Timestamp           | close_spy | close_qqq | spread | z_score | in_pair_position | side_a | side_b | entry_a | entry_b | qty_a | qty_b | pnl_total |
|---------------------|-----------|-----------|--------|---------|------------------|--------|--------|---------|---------|-------|-------|-----------|
| 2025-07-29 10:00:00 | 511.23    | 446.10    | 65.13  |  2.14   | TRUE             | -1     | 1      | 511.23  | 446.10  |  9    | 11    | 12.54     |

---

## 📘 Background & References

- [Pairs Trading (Investopedia)](https://www.investopedia.com/articles/active-trading/100215/pairs-trading-secret-profiting-market-neutral-strategies.asp)
- [Alpaca API Docs](https://alpaca.markets/docs/)
- ["Statistical Arbitrage in Pairs Trading Strategies"](https://www.cfainstitute.org/-/media/documents/article/rf-brief/rfbr-v5-n2-1-pdf.pdf) (Gatev, Goetzmann, Rouwenhorst)

---

## ⚠️ Disclaimer

- For education and research only. Not financial advice.
- Production usage requires additional error handling, real position monitoring, etc.
- Test thoroughly using Alpaca’s paper trading environment.

---

## ✉️ Support

Questions? Open an issue or contact the maintainer.

---

