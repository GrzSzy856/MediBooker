"""
api.py — Appointment search and booking for Medicover.
"""

import time

import requests

SLOTS_URL = "https://api-gateway-online24.medicover.pl/appointments/api/search-appointments/slots"
PRICES_URL = "https://api-gateway-online24.medicover.pl/payment-gateway/api/v1/visit-prices"
BOOKING_URL = "https://api-gateway-online24.medicover.pl/appointments/api/search-appointments/book-appointment"

FREE_PRICE = "0,00 zł"


def find_appointments(
    session: requests.Session,
    headers: dict,
    region_id: int,
    specialty_id: int,
    start_date: str,
) -> list[dict]:
    """
    Search for available appointment slots.
    Returns a list of slot dicts (raw API response items).
    Re-authenticates on 401 via the `reauth_fn` pattern — caller handles that.
    """
    params = {
        "RegionIds": region_id,
        "SpecialtyIds": specialty_id,
        "StartTime": start_date,
        "Page": 1,
        "PageSize": 100,
        "SlotSearchType": "Standard",
        "VisitType": "Center",
    }
    resp = session.get(SLOTS_URL, headers=headers, params=params)
    if resp.status_code == 401:
        raise PermissionError("401 — token expired, re-authenticate")
    resp.raise_for_status()

    data = resp.json()
    return data.get("items", [])


def book_appointment(
    session: requests.Session,
    headers: dict,
    slot: dict,
) -> bool:
    """
    Book a slot.
    First verifies the price is free (0,00 zł), then sends the booking request.
    Returns True on success, False if price is not free or booking fails.
    """
    clinic = slot.get("clinic", {})
    doctor = slot.get("doctor", {})
    specialty = slot.get("specialty", {})

    price_payload = {
        "visitDate": slot.get("appointmentDate"),
        "visitDetails": [
            {
                "clinicId": str(clinic.get("id", "")),
                "doctorId": str(doctor.get("id", "")),
                "specialtyId": str(specialty.get("id", "")),
            }
        ],
        "visitVariant": "Standard",
    }

    resp = session.post(PRICES_URL, headers=headers, json=price_payload)
    if resp.status_code == 401:
        raise PermissionError("401 — token expired, re-authenticate")
    resp.raise_for_status()

    prices = resp.json()
    if not prices:
        print("  [!] Empty price response — skipping booking")
        return False

    price = prices[0].get("price", "")
    if price != FREE_PRICE:
        print(f"  [!] Appointment price is not free: '{price}' — will not book")
        return False

    booking_payload = {
        "bookingString": slot.get("bookingString"),
        "metadata": {"appointmentSource": "Direct"},
    }
    time.sleep(1)
    resp = session.post(BOOKING_URL, headers=headers, json=booking_payload)
    if resp.status_code == 401:
        raise PermissionError("401 — token expired, re-authenticate")

    if resp.status_code in (200, 201):
        return True

    print(f"  [!] Booking failed, status {resp.status_code}: {resp.text}")
    return False
