import pandas as pd
from datetime import datetime
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")

# Trade keys
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")

# Create API object
BASE_URL = "https://paper-api.alpaca.markets"
trade_api = tradeapi.REST(TRADE_KEY, TRADE_SECRET, BASE_URL, api_version="v2")

# Get account information
account = trade_api.get_account()

# Print account info
print("Account ID:", account.id)
print("Status:", account.status)
print("Equity:", account.equity)
print("Buying Power:", account.buying_power)
print("Cash:", account.cash)
print("Portfolio Value:", account.portfolio_value)

# Convert account to DataFrame
account_frame = pd.DataFrame([account._raw])
print(f"Account DataFrame shape: {account_frame.shape}")

# Define output path
output_dir = os.path.join(os.getcwd(), "Account Info Files")
os.makedirs(output_dir, exist_ok=True)

current_time = datetime.now()
file_name = f"account_info_{current_time.strftime('%Y%m%d')}.csv"
file_path = os.path.join(output_dir, file_name)

# Save to CSV
account_frame.to_csv(file_path, index=False)
print(f"Finished saving account info to: {file_path}")
