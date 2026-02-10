from datetime import datetime
import pytz
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.calendar_client import get_calendar_client

print("\n=== Testing Calendar Client ===")
calendar = get_calendar_client()

# Test upcoming events (now with fallback)
try:
    events = calendar.get_upcoming_events(hours_ahead=48)
    if events:
        print(f"✅ Found {len(events)} potential high-impact events in next 48 hours")
        for event in events[:3]:
            print(f"   - {event['event']} ({event['country']}) at {event['datetime']}")
    else:
        print(f"✅ Calendar client working (no events detected in window)")
except Exception as e:
    print(f"⚠️  Calendar (optional): {e}")

# Test event proximity
try:
    now = datetime.now(pytz.UTC)
    nearby = calendar.check_event_proximity(now, window_minutes=360)
    if nearby:
        print(f"✅ Event nearby: {nearby['event']}")
    else:
        print(f"✅ No events detected in next 6 hours")
except Exception as e:
    print(f"⚠️  Event proximity check: {e}")