from decimal import Decimal
import os
import yfinance as yf
from typing import Dict, List
from datetime import datetime

# PythonAnywhere injects DOMAIN_SOCKET for native ASGI apps, but the spawned
# process does not inherit the proxy variables that are present in Bash
# consoles. Free accounts need the platform proxy for outbound market data.
if os.getenv("DOMAIN_SOCKET"):
    os.environ.setdefault("http_proxy", "http://proxy.server:3128")
    os.environ.setdefault("https_proxy", "http://proxy.server:3128")

class MarketDataError(Exception): pass
def get_price(nse_symbol:str)->Decimal:
    hist=yf.Ticker(f"{nse_symbol}.NS").history(period="5d",auto_adjust=False)
    if hist.empty: raise MarketDataError(f"No quote for {nse_symbol}")
    close=hist["Close"].dropna()
    if close.empty: raise MarketDataError(f"No close for {nse_symbol}")
    return Decimal(str(float(close.iloc[-1])))

def get_price_with_change(nse_symbol:str)->Dict:
    hist=yf.Ticker(f"{nse_symbol}.NS").history(period="5d",auto_adjust=False)
    if hist.empty: raise MarketDataError(f"No quote for {nse_symbol}")
    close=hist["Close"].dropna()
    if close.empty or len(close)<2: raise MarketDataError(f"Insufficient data for {nse_symbol}")
    current_price=float(close.iloc[-1])
    prev_price=float(close.iloc[-2])
    day_change=current_price-prev_price
    day_change_percent=(day_change/prev_price)*100 if prev_price!=0 else 0
    return {"current_price":Decimal(str(current_price)),"day_change":round(day_change,2),"day_change_percent":round(day_change_percent,2)}

def get_chart_data(nse_symbol: str, period: str = "1m") -> List[Dict]:
    """
    Fetch historical chart data for a stock
    period: 1d, 5d, 1m, 3m, 6m, 1y, 5y, max
    """
    period_map = {
        "1d": "1d",
        "5d": "5d",
        "1m": "1mo",
        "3m": "3mo",
        "6m": "6mo",
        "1y": "1y",
        "5y": "5y",
        "max": "max"
    }

    yf_period = period_map.get(period, "1mo")
    ticker = yf.Ticker(f"{nse_symbol}.NS")
    hist = ticker.history(period=yf_period, auto_adjust=False)

    if hist.empty:
        raise MarketDataError(f"No chart data available for {nse_symbol}")

    chart_data = []
    for index, row in hist.iterrows():
        chart_data.append({
            "time": index.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"])
        })

    return chart_data
