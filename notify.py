"""
notify.py — Send Telegram notifications via Bot API (plain requests, no library).
"""

import requests


def send(token: str, chat_id: str, message: str) -> bool:
    """
    Send a text message via Telegram Bot API.
    Returns True on success, False on failure.
    """
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return True
        print(f"  [!] Telegram error {resp.status_code}: {resp.text}")
        return False
    except requests.RequestException as e:
        print(f"  [!] Telegram request failed: {e}")
        return False
