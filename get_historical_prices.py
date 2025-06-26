import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")

# Data keys
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")

# Initialize Alpaca historical data client
data_client = StockHistoricalDataClient(DATA_KEY, DATA_SECRET)

# Get current NY time
ny_timezone = pytz.timezone("America/New_York")
current_time_ny = datetime.now(ny_timezone)
print("Date and time (NY):", current_time_ny.strftime("%Y-%m-%d %H:%M:%S"))

# Define UTC time range (last 10 minutes) in ISO format
utc_now = datetime.now(timezone.utc)
start_time = utc_now - timedelta(minutes=10)
start = start_time.isoformat()
end = utc_now.isoformat()

# Define symbol and request parameters
symbol = "AAPL"
request_params = StockBarsRequest(
    symbol_or_symbols=[symbol],
    timeframe=TimeFrame.Minute,
    start=start,
    end=end,
    limit=1000,
    feed="iex"
)

# Fetch historical bars
bars = data_client.get_stock_bars(request_params)

# Handle response safely
bars_data = bars.data.get(symbol)
if bars_data:
    # Convert to DataFrame
    price_bars = pd.DataFrame([bar.model_dump() for bar in bars_data])

    # Create output directory and filename
    output_dir = os.path.join(os.getcwd(), "Historical Files")
    os.makedirs(output_dir, exist_ok=True)

    current_time = datetime.now()
    file_name = f"price_bars_{current_time.strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(output_dir, file_name)

    # Save to CSV
    price_bars.to_csv(file_path, index=False)
    print(f"Finished getting historical OHLCV stock prices and saved to: {file_path}")
else:
    print(f"No historical data returned for symbol: {symbol}")
