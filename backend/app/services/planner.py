from decimal import Decimal
import logging
from .market_data import get_price_with_change

logger = logging.getLogger(__name__)

def classify(price,minimum,maximum):
    if price is None:return "REVIEW","No usable market price."
    if minimum is not None and price<minimum:return "BUY","Below preferred accumulation range."
    if maximum is not None and price<=maximum:return "BUY","Inside preferred accumulation range."
    return "WAIT","Above preferred accumulation range."
def build_recommendations(stocks,stock_budget=35000,mf_budget=30000):
    # Separate stocks and mutual funds
    stock_items = [s for s in stocks if s.instrument_type == "stock"]
    mf_items = [s for s in stocks if s.instrument_type == "mutual_fund"]

    # Calculate separate totals
    stock_total_target = sum(s.monthly_target for s in stock_items)
    mf_total_target = sum(s.monthly_target for s in mf_items)

    out=[]

    # Process stocks with stock budget
    for s in stock_items:
        try:
            price_data=get_price_with_change(s.symbol)
            price=price_data["current_price"]
            day_change=price_data["day_change"]
            day_change_percent=price_data["day_change_percent"]
        except Exception:
            logger.exception("Market data retrieval failed for %s", s.symbol)
            price=None
            day_change=None
            day_change_percent=None
        status,reason=classify(price,s.min_buy,s.max_buy)
        suggested=s.max_buy if s.max_buy is not None else price
        allocation_ratio=Decimal(s.monthly_target)/Decimal(stock_total_target) if stock_total_target>0 else Decimal(0)
        adjusted_target=int(Decimal(stock_budget)*allocation_ratio)
        qty=int(Decimal(adjusted_target)//price) if status=="BUY" and price and price>0 else 0
        deploy=(price*qty).quantize(Decimal("0.01")) if qty else Decimal("0")
        out.append(dict(symbol=s.symbol,name=s.name,instrument_type=s.instrument_type,market_cap=s.market_cap,current_price=price,day_change=day_change,day_change_percent=day_change_percent,target_amount=adjusted_target,suggested_price=suggested,quantity=qty,deploy_amount=deploy,status=status,reason=reason))

    # Process mutual funds with MF budget
    for s in mf_items:
        allocation_ratio=Decimal(s.monthly_target)/Decimal(mf_total_target) if mf_total_target>0 else Decimal(0)
        adjusted_target=int(Decimal(mf_budget)*allocation_ratio)
        out.append(dict(symbol=s.symbol,name=s.name,instrument_type=s.instrument_type,market_cap=s.market_cap,current_price=None,day_change=None,day_change_percent=None,target_amount=adjusted_target,suggested_price=None,quantity=0,deploy_amount=Decimal(adjusted_target),status="BUY",reason="Monthly SIP allocation"))

    return out
def summarize(rows,budget):
    deployed=sum((r["deploy_amount"] for r in rows),Decimal("0")); return deployed,max(Decimal(budget)-deployed,Decimal("0"))
