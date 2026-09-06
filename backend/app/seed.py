from decimal import Decimal
from .db import init_db,SessionLocal
from .models import Stock
DATA=[("ICICI Bank","ICICIBANK","large","Banking",6000,1400,1415),("Bharti Airtel","BHARTIARTL","large","Telecom",4500,1920,1945),("Larsen & Toubro","LT","large","Infrastructure",4500,4050,4090),("Reliance Industries","RELIANCE","large","Diversified",3500,1295,1315),("HDFC Bank","HDFCBANK","large","Banking",3000,720,730),("Max Healthcare","MAXHEALTH","mid","Healthcare",3000,970,1000),("KFin Technologies","KFINTECH","mid","Financial Infrastructure",3000,930,960),("Indian Hotels","INDHOTEL","mid","Hospitality",3000,700,720),("TD Power Systems","TDPOWERSYS","small","Industrial Manufacturing",2500,None,None)]
def main():
    init_db()
    with SessionLocal() as db:
        if db.query(Stock).count(): return
        for name,symbol,cap,sector,target,mi,ma in DATA: db.add(Stock(name=name,symbol=symbol,market_cap=cap,sector=sector,monthly_target=target,min_buy=Decimal(str(mi)) if mi else None,max_buy=Decimal(str(ma)) if ma else None,notes="Review before each monthly purchase."))
        db.commit(); print("Seeded")
if __name__=="__main__": main()
