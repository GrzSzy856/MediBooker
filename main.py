"""
main.py — MediBooker entry point.

Modes:
  POLL=false  → authenticate, search once, print + optionally book, exit
  POLL=true   → loop every POLL_INTERVAL_SEC seconds, only notify on new slots

All config via .env — see .env.example.
"""

import sys
import time

from dotenv import load_dotenv
import os

load_dotenv()

# --- Config ---
CARD_NUMBER = os.getenv("MEDICOVER_CARD_NUMBER", "")
PASSWORD = os.getenv("MEDICOVER_PASSWORD", "")
REGION_ID = int(os.getenv("REGION_ID", "204"))
SPECIALTY_ID = int(os.getenv("SPECIALTY_ID", "9"))
START_DATE = os.getenv("START_DATE", "").split("#")[0].strip()      # e.g. "2025-04-01"
END_DATE = os.getenv("END_DATE", "").split("#")[0].strip()          # e.g. "2025-05-01"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"
AUTO_BOOK = os.getenv("AUTO_BOOK", "false").lower() == "true"
POLL = os.getenv("POLL", "false").lower() == "true"
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "300"))
APPOINTMENT_TIME_RANGE = os.getenv("APPOINTMENT_TIME_RANGE", "")   # e.g. "16-24"
DOCTOR_NAME = os.getenv("DOCTOR_NAME", "").strip()                  # e.g. "Adam Nowak"

MAX_REAUTH_ATTEMPTS = 7
REAUTH_WAIT_SEC = 30

import auth
import api
import notify


def _slot_id(slot: dict) -> str:
    """Unique identifier for a slot — used to deduplicate across poll cycles."""
    return slot.get("bookingString", "") or str(slot.get("appointmentDate", ""))


def _format_slot(slot: dict) -> str:
    clinic = slot.get("clinic", {}).get("name", "?")
    doctor = slot.get("doctor", {}).get("name", "?")
    specialty = slot.get("specialty", {}).get("name", "?")
    date = slot.get("appointmentDate", "?")
    return f"  • {date} | {specialty} | {doctor} | {clinic}"


def _apply_filters(slots: list) -> list:
    result = slots
    if APPOINTMENT_TIME_RANGE:
        start_h, end_h = (int(x) for x in APPOINTMENT_TIME_RANGE.split("-"))
        def in_range(slot):
            dt_str = slot.get("appointmentDate", "")
            try:
                hour = int(dt_str[11:13])  # "2025-04-15T16:30:00" → 16
                return start_h <= hour < end_h
            except (ValueError, IndexError):
                return True
        result = [s for s in result if in_range(s)]
    if END_DATE:
        result = [s for s in result if s.get("appointmentDate", "")[:10] <= END_DATE]
    if DOCTOR_NAME:
        name_lower = DOCTOR_NAME.lower()
        result = [s for s in result if name_lower in s.get("doctor", {}).get("name", "").lower()]
    return result


def authenticate() -> tuple:
    """Authenticate with retry logic. Returns (session, headers)."""
    for attempt in range(1, MAX_REAUTH_ATTEMPTS + 1):
        try:
            print(f"Authenticating (attempt {attempt}/{MAX_REAUTH_ATTEMPTS})...")
            session, headers = auth.login(CARD_NUMBER, PASSWORD)
            token_prefix = headers.get("Authorization", "")[:30]
            print(f"Authenticated: {token_prefix}...")
            return session, headers
        except Exception as e:
            print(f"  [!] Auth failed: {e}")
            if attempt < MAX_REAUTH_ATTEMPTS:
                print(f"  Retrying in {REAUTH_WAIT_SEC}s...")
                time.sleep(REAUTH_WAIT_SEC)
    print("  [!] All authentication attempts failed. Exiting.")
    sys.exit(1)


def search_and_handle(session, headers, seen_ids: set) -> tuple[list[dict], set]:
    """
    Search for appointments. Returns (new_slots, updated_seen_ids).
    On 401, re-authenticates once and retries.
    """
    for attempt in range(2):
        try:
            slots = api.find_appointments(session, headers, REGION_ID, SPECIALTY_ID, START_DATE)
            break
        except PermissionError:
            if attempt == 0:
                print("  [!] 401 received — re-authenticating...")
                session, headers = authenticate()
            else:
                print("  [!] Still 401 after re-auth. Skipping this cycle.")
                return [], seen_ids
        except Exception as e:
            print(f"  [!] Search error: {e}")
            return [], seen_ids

    new_slots = _apply_filters([s for s in slots if _slot_id(s) not in seen_ids])
    new_seen = seen_ids | {_slot_id(s) for s in slots}
    return new_slots, new_seen


def handle_slots(session, headers, new_slots: list[dict]):
    """Print, notify, and optionally book new slots."""
    if not new_slots:
        print("  No new slots found.")
        return

    print(f"  Found {len(new_slots)} new slot(s):")
    lines = [_format_slot(s) for s in new_slots]
    for line in lines:
        print(line)

    msg = f"<b>MediBooker — {len(new_slots)} new slot(s) found</b>\n" + "\n".join(lines)
    if TELEGRAM_ENABLED:
        notify.send(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

    if AUTO_BOOK:
        slot = new_slots[0]
        print(f"\n  AUTO_BOOK=true — attempting to book:\n{_format_slot(slot)}")
        try:
            success = api.book_appointment(session, headers, slot)
        except PermissionError:
            print("  [!] 401 during booking — re-authenticating and retrying...")
            session, headers = authenticate()
            success = api.book_appointment(session, headers, slot)

        if success:
            booked_msg = f"Booked appointment:\n{_format_slot(slot)}"
            print(f"  Booking confirmed!")
            if TELEGRAM_ENABLED:
                notify.send(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, f"<b>Booked!</b>\n{_format_slot(slot)}")
        else:
            print("  Booking failed or not free.")


def main():
    if not CARD_NUMBER or not PASSWORD:
        print("Error: MEDICOVER_CARD_NUMBER and MEDICOVER_PASSWORD must be set in .env")
        sys.exit(1)

    session, headers = authenticate()
    seen_ids: set = set()

    if not POLL:
        # --- Run once ---
        print(f"\nSearching: region={REGION_ID}, specialty={SPECIALTY_ID}, from={START_DATE}")
        new_slots, seen_ids = search_and_handle(session, headers, seen_ids)
        handle_slots(session, headers, new_slots)
    else:
        # --- Poll loop ---
        print(f"\nPoll mode: checking every {POLL_INTERVAL_SEC}s. Press Ctrl+C to stop.")
        cycle = 0
        while True:
            cycle += 1
            print(f"\n[Cycle {cycle}] {time.strftime('%Y-%m-%d %H:%M:%S')} — searching...")
            new_slots, _ = search_and_handle(session, headers, set())
            handle_slots(session, headers, new_slots)
            print(f"  Sleeping {POLL_INTERVAL_SEC}s...")
            time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
