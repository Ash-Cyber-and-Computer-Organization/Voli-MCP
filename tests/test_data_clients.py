"""Test Twelve Data and Calendar clients"""

from src.data.twelve_data_client import get_client
from src.data.calendar_client import get_calendar_client
from datetime import datetime, timedelta
import pytz

print("=== Testing Twelve Data Client ===")
client = get_client()

# Test quote
try:
    quote = client.get_quote("EUR/USD")
    print(f"✅ EUR/USD Quote: {quote.get('price', 'N/A')}")
except Exception as e:
    print(f"❌ Quote failed: {e}")

# Test intraday data
try:
    df = client.get_intraday_data("GBP/USD", interval="5min", outputsize=10)
    print(f"✅ Intraday data: {len(df)} candles")
    print(f"   Latest: {df.index[-1]} - Close: {df['close'].iloc[-1]}")
except Exception as e:
    print(f"❌ Intraday failed: {e}")

# Test historical data
try:
    df_hist = client.get_historical_sessions("EUR/USD", days_back=30, interval="5min")
    print(f"✅ Historical data: {len(df_hist)} candles over ~30 days")
except Exception as e:
    print(f"❌ Historical failed: {e}")

# Rate limit status
status = client.get_rate_limit_status()
print(f"\n📊 Rate Limits: {status['requests_today']}/{status['daily_limit']} used ({status['percentage_used']}%)")

print("\n=== Testing Calendar Client ===")
calendar = get_calendar_client()

# Test upcoming events
try:
    events = calendar.get_upcoming_events(hours_ahead=48)
    print(f"✅ Found {len(events)} high-impact events in next 48 hours")
    for event in events[:3]:
        print(f"   - {event['event']} ({event['country']}) at {event['datetime']}")
except Exception as e:
    print(f"⚠️  Calendar (optional): {e}")

# Test event proximity
try:
    now = datetime.now(pytz.UTC)
    nearby = calendar.check_event_proximity(now, window_minutes=360)
    if nearby:
        print(f"✅ Event nearby: {nearby['event']}")
    else:
        print(f"✅ No events in next 6 hours")
except Exception as e:
    print(f"⚠️  Event proximity check: {e}")

print("\n✅ Data clients ready!")