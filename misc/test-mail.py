import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import os
import time
from datetime import datetime, timezone, timedelta
import pytz
import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from ta.trend import MACD
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# EMAIL_USER = "YOUR_EMAIL@gmail.com"
# EMAIL_PASSWORD = "YOUR_APP_PASSWORD"
# EMAIL_RECEIVER = "YOUR_EMAIL@gmail.com"

load_dotenv("/Users/chintzruparel/Documents/GitHub/startup/.env")
# ALPACA API KEYS
DATA_KEY = os.getenv("DATA_KEY")
DATA_SECRET = os.getenv("DATA_SECRET")
TRADE_KEY = os.getenv("TRADE_KEY")
TRADE_SECRET = os.getenv("TRADE_SECRET")

#GMAIL API KEYS
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

def send_trade_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_RECEIVER, msg.as_string())

send_trade_email(
    subject="✅ TEST EMAIL from Python",
    body="This is just a test to confirm your SMTP + App Password are working!"
)
