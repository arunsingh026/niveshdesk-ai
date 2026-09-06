from decimal import Decimal
from app.services.planner import classify
def test_inside(): assert classify(Decimal("1410"),Decimal("1400"),Decimal("1415"))[0]=="BUY"
def test_above(): assert classify(Decimal("1500"),Decimal("1400"),Decimal("1415"))[0]=="WAIT"
def test_missing(): assert classify(None,Decimal("1400"),Decimal("1415"))[0]=="REVIEW"
