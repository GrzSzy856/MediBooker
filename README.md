# MediBooker

A lightweight Python script that watches for available Medicover appointments and optionally books the first free slot automatically.

> **Requirements:** A valid Medicover account with an active subscription. MFA must be **disabled** on your account (the script cannot handle SMS codes).

---

## Features

- One-shot search or continuous polling mode
- Telegram notifications when new slots appear
- Auto-booking of the first free slot (price must be `0,00 zł`)
- Automatic re-authentication on token expiry (up to 7 retries)

---

## Quick Start

### 1. Clone / download

```bash
git clone <repo-url>
cd MediBooker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies: `requests`, `beautifulsoup4`, `python-dotenv`, `fake-useragent`

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` with your values (see [Configuration](#configuration) below).

### 4. Run

```bash
python main.py
```

---

## Configuration

All settings are read from the `.env` file (or from real environment variables — env vars take precedence).

| Variable               | Required | Default       | Description                                                      |
| ---------------------- | -------- | ------------- | ---------------------------------------------------------------- |
| `MEDICOVER_CARD_NUMBER`| Yes      | —             | Your Medicover card / login number                               |
| `MEDICOVER_PASSWORD`   | Yes      | —             | Your Medicover account password                                  |
| `REGION_ID`            | Yes      | `204`         | Region to search in (see [Finding IDs](#finding-ids))            |
| `SPECIALTY_ID`         | Yes      | `9`           | Medical specialty to search for                                  |
| `START_DATE`           | Yes      | `2025-04-01`  | Earliest acceptable appointment date (`YYYY-MM-DD`)              |
| `TELEGRAM_TOKEN`       | No       | —             | Telegram bot token — needed for notifications                    |
| `TELEGRAM_CHAT_ID`     | No       | —             | Your Telegram chat ID — needed for notifications                 |
| `AUTO_BOOK`            | No       | `false`       | Set to `true` to automatically book the first free slot found    |
| `POLL`                 | No       | `false`       | Set to `true` to run in continuous polling mode                  |
| `POLL_INTERVAL_SEC`    | No       | `300`         | Seconds between polls (only used when `POLL=true`)               |

### Example `.env`

```dotenv
# Medicover credentials
MEDICOVER_CARD_NUMBER=your_card_number
MEDICOVER_PASSWORD=yourpassword

# Search criteria
REGION_ID=204          # 204 = Warszawa
SPECIALTY_ID=9         # 9 = General Practitioner
START_DATE=2025-04-01

# Telegram notifications (optional but recommended)
TELEGRAM_TOKEN=123456:ABC-xyz...
TELEGRAM_CHAT_ID=123456789

# Auto-book first free slot (default: false)
# WARNING: booking happens without any confirmation prompt
AUTO_BOOK=false

# Polling mode
POLL=false
POLL_INTERVAL_SEC=300
```

---

## Modes of Operation

### One-shot (default)

Authenticates, searches once, prints results, sends a Telegram notification if slots are found, optionally books, then exits.

```bash
POLL=false python main.py
```

### Polling

Loops indefinitely, checking every `POLL_INTERVAL_SEC` seconds. Only **new** slots (not seen in previous cycles) trigger a notification. Press `Ctrl+C` to stop.

```bash
POLL=true POLL_INTERVAL_SEC=120 python main.py
```

---

## Auto-booking

When `AUTO_BOOK=true`, MediBooker will:

1. Find the first new slot.
2. Verify the price is `0,00 zł` (free under insurance). If it is not free, the slot is skipped.
3. Send a booking request.
4. Send a Telegram notification confirming the booking.

> **Warning:** With `AUTO_BOOK=true` an appointment is booked immediately without further confirmation. Use with care.

---

## Telegram Notifications

To receive notifications:

1. Create a bot via [@BotFather](https://t.me/botfather) and copy the token.
2. Get your chat ID — send any message to your bot, then visit:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   and look for `"chat": {"id": ...}` in the response.
3. Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.

Notifications are sent in HTML format and include the date, specialty, doctor, and clinic for each slot found.

---

## Finding IDs

MediBooker needs numeric IDs for region and specialty. The easiest way to find them is to log in to [online24.medicover.pl](https://online24.medicover.pl), open your browser's developer tools (F12 → Network tab), start filtering appointments, and inspect the outgoing API request — the query parameters will show the IDs.

Common values:

| Name                     | Type      | ID     |
| ------------------------ | --------- | ------ |
| Warszawa                 | Region    | `204`  |
| Kraków                   | Region    | `200`  |
| General Practitioner     | Specialty | `9`    |
| Pediatrician             | Specialty | `132`  |

---

## Project Structure

```
MediBooker/
├── main.py          # Entry point — config, polling loop, orchestration
├── auth.py          # OAuth2 PKCE login flow
├── api.py           # Appointment search and booking API calls
├── notify.py        # Telegram notification helper
├── requirements.txt # Python dependencies
└── .env.example     # Configuration template
```

---

## Troubleshooting

**Authentication fails**
- Double-check `MEDICOVER_CARD_NUMBER` and `MEDICOVER_PASSWORD`.
- Make sure MFA is disabled on your Medicover account.
- The script retries up to 7 times with 30-second delays before giving up.

**No slots found**
- Try an earlier `START_DATE`.
- Verify `REGION_ID` and `SPECIALTY_ID` are correct for your area and need.

**Telegram notifications not arriving**
- Confirm the bot token and chat ID are correct.
- Make sure you have started a conversation with the bot (send it `/start` first).

**Booking fails**
- The appointment price must be `0,00 zł`. Paid slots are intentionally skipped.
- If the slot disappears between search and booking, the request will return a non-2xx status and be reported in the console.
