import os, json, asyncio
from datetime import datetime, timedelta
import pytz
from tools.session_analyzer import analyze_forex_session

async def run():
    # EURUSD London Open
    os.environ.pop("CALENDAR_OVERRIDE_EVENTS", None)
    print(await analyze_forex_session("EUR/USD", "london"))

    # GBPUSD NY session with NFP day (override)
    nfp_time = datetime.now(pytz.UTC) + timedelta(hours=1)
    os.environ["CALENDAR_OVERRIDE_EVENTS"] = json.dumps([{
        "event": "US Non-Farm Payrolls (NFP)",
        "currency": "USD",
        "country": "USD",
        "datetime": nfp_time.isoformat(),
        "impact": "high",
        "event_type": "NFP",
        "source": "override"
    }])
    print(await analyze_forex_session("GBP/USD", "ny"))

    # USDJPY Asia session with no events
    os.environ["CALENDAR_OVERRIDE_EVENTS"] = json.dumps([])
    print(await analyze_forex_session("USD/JPY", "asian"))

asyncio.run(run())