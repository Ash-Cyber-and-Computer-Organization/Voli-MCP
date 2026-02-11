"""Quick tests for utility modules"""

from src.utils.sessions import *
from src.utils.formatters import *
from datetime import datetime
import pytz

print("=== Testing Sessions ===")
print(f"Current session: {get_current_session()}")
print(f"Is weekend: {is_weekend()}")
next_sess, next_time = get_next_session()
print(f"Next session: {next_sess} at {next_time}")
print(f"Session overlap: {is_session_overlap()}")

print("\n=== Testing Formatters ===")
print(f"Normalize EUR/USD: {normalize_pair_format('EUR/USD')}")
print(f"Display GBPJPY: {display_pair_format('GBPJPY')}")
print(f"EUR/USD pip value: {get_pip_value('EUR/USD')}")
print(f"USD/JPY pip value: {get_pip_value('USD/JPY')}")
print(f"50 pips movement on EUR/USD: {pips_to_price(50, 'EUR/USD')}")

print("\n=== All Pairs ===")
pairs = get_supported_pairs()
print(f"Majors ({len(pairs['majors'])}): {', '.join(pairs['majors'][:3])}...")
print(f"Minors ({len(pairs['minors'])}): {', '.join(pairs['minors'][:3])}...")
print(f"Total supported pairs: {len(ALL_PAIRS)}")

print("\n✅ All utilities working!")