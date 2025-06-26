import pandas as pd
from datetime import datetime
import pytz
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")

# Trade keys
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")

# Initialize client
trading_client = TradingClient(TRADE_KEY, TRADE_SECRET)

# Get closed orders (change to OPEN if needed)
orders = trading_client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.CLOSED))

# Convert orders to DataFrame
orders_frame = pd.DataFrame([order.__dict__ for order in orders])
print(f"Orders DataFrame shape: {orders_frame.shape}")

# Generate dynamic filename
ny_timezone = pytz.timezone("America/New_York")
current_time = datetime.now(ny_timezone)
file_name = f"orders_{current_time.strftime('%Y%m%d')}.csv"

# Create output directory and save file
output_dir = os.path.join(os.getcwd(), "Order Files")
os.makedirs(output_dir, exist_ok=True)
file_path = os.path.join(output_dir, file_name)
orders_frame.to_csv(file_path, index=False)
print(f"Finished getting orders and saved to: {file_path}")

# Print order client IDs and order IDs
for order in orders:
    print(f"Client Order ID: {order.client_order_id}")
    print(f"Order ID: {order.id}")
