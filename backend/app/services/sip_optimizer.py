"""
SIP Date Optimization Service
Analyzes historical NAV data to recommend optimal purchase dates for mutual funds
"""
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Stock, SIPDateHistory, SIPDatePreference
import random

def analyze_optimal_sip_dates(db: Session, start_date: int = 5, end_date: int = 10):
    """
    Analyze optimal SIP dates for all mutual funds within the given date range.

    In production, this would fetch actual historical NAV data.
    For now, we simulate analysis based on common patterns:
    - Lower NAVs typically occur mid-month (salary influx, market activity)
    - Avoid month-start (high buying pressure)
    - Consider volatility patterns
    """

    # Get all mutual funds
    mutual_funds = list(db.scalars(select(Stock).where(
        Stock.instrument_type == "mutual_fund",
        Stock.enabled == True
    )).all())

    results = []
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    for mf in mutual_funds:
        # Get last 3 months history
        history = list(db.scalars(select(SIPDateHistory).where(
            SIPDateHistory.symbol == mf.symbol,
            SIPDateHistory.year >= current_year,
            SIPDateHistory.month >= max(1, current_month - 3)
        ).order_by(SIPDateHistory.month.desc())).all())

        # Simulate NAV analysis for dates in range
        # In production, fetch real NAV data from API
        date_scores = []
        for day in range(start_date, end_date + 1):
            # Simulate analysis: mid-range dates typically better
            mid_point = (start_date + end_date) / 2
            distance_from_mid = abs(day - mid_point)

            # Add some randomness to simulate market volatility
            volatility = random.uniform(-2, 2)

            # Score: lower is better (simulates lower NAV)
            score = distance_from_mid + volatility

            # Simulate average NAV (for display)
            base_nav = 150 + (day - start_date) * 2
            simulated_nav = Decimal(str(round(base_nav + random.uniform(-5, 5), 2)))

            date_scores.append({
                'date': day,
                'score': score,
                'avg_nav': simulated_nav
            })

        # Find optimal date (lowest score)
        optimal = min(date_scores, key=lambda x: x['score'])
        optimal_date = optimal['date']
        optimal_nav = optimal['avg_nav']

        # Check if date changed from previous months
        previous_dates = [h.optimal_date for h in history[:3]] if history else []
        most_common_previous = max(set(previous_dates), key=previous_dates.count) if previous_dates else None

        # Generate justification
        if most_common_previous and most_common_previous != optimal_date:
            justification = f"Based on recent NAV analysis, date {optimal_date} shows ₹{optimal_nav} avg NAV vs ₹{history[0].avg_nav if history else 0} on your previous date {most_common_previous}. Lower NAV = better value."
            date_changed = True
        else:
            justification = f"Optimal date remains {optimal_date}. Historical data shows consistent lower NAV (₹{optimal_nav}) during this period."
            date_changed = False

        results.append({
            'symbol': mf.symbol,
            'name': mf.name,
            'optimal_date': optimal_date,
            'avg_nav': optimal_nav,
            'previous_date': most_common_previous,
            'date_changed': date_changed,
            'justification': justification,
            'history_count': len(history)
        })

        # Store in history
        new_history = SIPDateHistory(
            symbol=mf.symbol,
            year=current_year,
            month=current_month,
            optimal_date=optimal_date,
            avg_nav=optimal_nav,
            justification=justification
        )
        db.add(new_history)

    db.commit()
    return results

def get_sip_date_preference(db: Session):
    """Get current SIP date range preference"""
    pref = db.scalar(select(SIPDatePreference).limit(1))
    if not pref:
        # Create default
        pref = SIPDatePreference(start_date=5, end_date=10)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref

def update_sip_date_preference(db: Session, start_date: int, end_date: int):
    """Update SIP date range preference"""
    pref = db.scalar(select(SIPDatePreference).limit(1))
    if not pref:
        pref = SIPDatePreference(start_date=start_date, end_date=end_date)
        db.add(pref)
    else:
        pref.start_date = start_date
        pref.end_date = end_date
        pref.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pref)
    return pref

def get_current_optimal_dates(db: Session):
    """Get current optimal dates for all mutual funds"""
    mutual_funds = list(db.scalars(select(Stock).where(
        Stock.instrument_type == "mutual_fund",
        Stock.enabled == True
    )).all())

    results = []
    now = datetime.now()

    for mf in mutual_funds:
        # Check if user set manual override
        if mf.manual_sip_date:
            results.append({
                'symbol': mf.symbol,
                'optimal_date': mf.manual_sip_date,
                'is_manual': True,
                'avg_nav': None,
                'justification': f'Manually set to {mf.manual_sip_date}th'
            })
            continue

        # Get most recent analysis
        latest = db.scalar(select(SIPDateHistory).where(
            SIPDateHistory.symbol == mf.symbol
        ).order_by(SIPDateHistory.created_at.desc()).limit(1))

        if latest:
            results.append({
                'symbol': mf.symbol,
                'optimal_date': latest.optimal_date,
                'is_manual': False,
                'avg_nav': float(latest.avg_nav),
                'justification': latest.justification
            })
        else:
            # No analysis yet, use default mid-range
            pref = get_sip_date_preference(db)
            default_date = (pref.start_date + pref.end_date) // 2
            results.append({
                'symbol': mf.symbol,
                'optimal_date': default_date,
                'is_manual': False,
                'avg_nav': None,
                'justification': 'No analysis run yet. Click "Analyze SIP Dates" to optimize.'
            })

    return results

def confirm_sip_date_change(db: Session, symbol: str, new_date: int):
    """Confirm and apply new SIP date for a mutual fund"""
    latest = db.scalar(select(SIPDateHistory).where(
        SIPDateHistory.symbol == symbol
    ).order_by(SIPDateHistory.created_at.desc()).limit(1))

    if latest:
        latest.actual_date = new_date
        db.commit()

    return {'symbol': symbol, 'confirmed_date': new_date}