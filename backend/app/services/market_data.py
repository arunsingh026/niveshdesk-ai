from decimal import Decimal
import os
import re
import time
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener

# PythonAnywhere's native ASGI worker does not inherit the proxy variables that
# are present in Bash consoles. Free accounts need the platform proxy for
# outbound market data. The home path keeps this hosting-specific workaround
# out of local and container environments.
IS_PYTHONANYWHERE = os.path.isdir("/home/arunsingh026")
PYTHONANYWHERE_PROXY = "http://proxy.server:3128"
if IS_PYTHONANYWHERE:
    for proxy_variable in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
        os.environ[proxy_variable] = PYTHONANYWHERE_PROXY

import yfinance as yf
from typing import Dict, List
from datetime import datetime

PRICE_CACHE_TTL_SECONDS = 300
_price_cache: Dict[str, tuple[float, Dict]] = {}


def _get_google_finance_price(nse_symbol: str) -> Decimal:
    url = f"https://www.google.com/finance/quote/{quote(nse_symbol, safe='')}:NSE?hl=en"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = build_opener(ProxyHandler({"https": PYTHONANYWHERE_PROXY}))
    page = opener.open(request, timeout=20).read().decode("utf-8", errors="replace")
    match = re.search(
        r'jsname="Pdsbrc"[^>]*>\s*<span>₹\s*([0-9,]+(?:\.[0-9]+)?)',
        page,
    )
    if not match:
        raise MarketDataError(f"No Google Finance quote for {nse_symbol}")
    return Decimal(match.group(1).replace(",", ""))


class MarketDataError(Exception): pass
def get_price(nse_symbol:str)->Decimal:
    return get_price_with_change(nse_symbol)["current_price"]

def get_price_with_change(nse_symbol:str)->Dict:
    cached = _price_cache.get(nse_symbol)
    now = time.monotonic()
    if cached and now - cached[0] < PRICE_CACHE_TTL_SECONDS:
        return cached[1]

    if IS_PYTHONANYWHERE:
        result = {
            "current_price": _get_google_finance_price(nse_symbol),
            "day_change": None,
            "day_change_percent": None,
        }
        _price_cache[nse_symbol] = (now, result)
        return result

    hist=yf.Ticker(f"{nse_symbol}.NS").history(period="5d",auto_adjust=False)
    if hist.empty: raise MarketDataError(f"No quote for {nse_symbol}")
    close=hist["Close"].dropna()
    if close.empty or len(close)<2: raise MarketDataError(f"Insufficient data for {nse_symbol}")
    current_price=float(close.iloc[-1])
    prev_price=float(close.iloc[-2])
    day_change=current_price-prev_price
    day_change_percent=(day_change/prev_price)*100 if prev_price!=0 else 0
    result = {"current_price":Decimal(str(current_price)),"day_change":round(day_change,2),"day_change_percent":round(day_change_percent,2)}
    _price_cache[nse_symbol] = (now, result)
    return result

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
