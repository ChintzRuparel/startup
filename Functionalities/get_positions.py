import pandas as pd
from datetime import datetime
import pytz
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")

# Trade keys
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")

# Initialize client
trading_client = TradingClient(TRADE_KEY, TRADE_SECRET)

# Get all open positions
portfolio = trading_client.get_all_positions()

for position in portfolio:
    print(f"Symbol: {position.symbol}, Qty: {position.qty}, Side: {position.side}, Unreal_PnL: {position.unrealized_pl}")

# Analyze first position
position = portfolio[0]
qty = int(position.qty)

if qty < 0:
    print(f"Your first position is a short position of {qty} shares of {position.symbol}, with an unrealized PnL of: {position.unrealized_pl}")
else:
    print(f"Your first position is a long position of {qty} shares of {position.symbol}, with an unrealized PnL of: {position.unrealized_pl}")

# Convert to DataFrame
position_frame = pd.DataFrame([pos.__dict__ for pos in portfolio])  # Use all positions

# Generate output file path
ny_timezone = pytz.timezone("America/New_York")
current_time = datetime.now(ny_timezone)
file_name = f"positions_{current_time.strftime('%Y%m%d')}.csv"

# Define path to save file
output_dir = os.path.join(os.getcwd(), "Position Files")
os.makedirs(output_dir, exist_ok=True)  # Create folder if it doesn't exist
file_path = os.path.join(output_dir, file_name)

# Save file
position_frame.to_csv(file_path, index=False)
print(f"Finished getting position frame and saved to: {file_path}")
