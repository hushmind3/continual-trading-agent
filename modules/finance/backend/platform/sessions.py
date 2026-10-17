"""Exchange holidays and shortened sessions, with bounded daily lookup caching."""
from functools import lru_cache
from datetime import timedelta
from zoneinfo import ZoneInfo

VENUES={'KRX':('XKRX','Asia/Seoul'),'KOSDAQ':('XKRX','Asia/Seoul'),
        'US':('NYSE','America/New_York'),'Japan':('JPX','Asia/Tokyo'),
        'HongKong':('XHKG','Asia/Hong_Kong'),'Germany':('XETR','Europe/Berlin'),'UK':('LSE','Europe/London')}


@lru_cache(maxsize=64)
def schedule(market,day):
    import pandas_market_calendars as calendars
    calendar=calendars.get_calendar(VENUES[market][0])
    row=calendar.schedule(start_date=day,end_date=day)
    return None if row.empty else (row.iloc[0].market_open.to_pydatetime(),row.iloc[0].market_close.to_pydatetime())


def session_open(market,now):
    if market not in VENUES:return None
    zone=ZoneInfo(VENUES[market][1]); local=now.astimezone(zone)
    try:
        hours=schedule(market,local.date().isoformat())
    except (RuntimeError,KeyError):
        return None
    if hours is None:return False
    opening,closing=hours
    if market=='US':
        opening=local.replace(hour=4,minute=0,second=0,microsecond=0)
        closing=closing+timedelta(hours=4)
    return opening<=now<=closing+timedelta(minutes=2)
