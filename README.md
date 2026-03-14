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
| `START_DATE`           | No       | —             | Earliest acceptable appointment date (`YYYY-MM-DD`); no limit if blank |
| `END_DATE`             | No       | —             | Latest acceptable appointment date (`YYYY-MM-DD`); no limit if blank |
| `TELEGRAM_ENABLED`     | No       | `true`        | Set to `false` to disable Telegram notifications entirely        |
| `TELEGRAM_TOKEN`       | No       | —             | Telegram bot token                                               |
| `TELEGRAM_CHAT_ID`     | No       | —             | Your Telegram chat ID                                            |
| `AUTO_BOOK`            | No       | `false`       | Set to `true` to automatically book the first free slot found    |
| `POLL`                 | No       | `false`       | Set to `true` to run in continuous polling mode                  |
| `POLL_INTERVAL_SEC`    | No       | `300`         | Seconds between polls (only used when `POLL=true`)               |
| `APPOINTMENT_TIME_RANGE` | No     | —             | Hour range filter, e.g. `16-24` (only slots from 16:00 to 23:59) |
| `DOCTOR_NAME`          | No       | —             | Partial doctor name filter, e.g. `Nowak` (case-insensitive)      |

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

# Optional filters (leave blank to disable)
# APPOINTMENT_TIME_RANGE: e.g. 16-24 (only slots from 16:00 to 23:59)
APPOINTMENT_TIME_RANGE=16-24
# DOCTOR_NAME: partial match, case-insensitive
DOCTOR_NAME=Nowak

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

MediBooker needs numeric IDs for region and specialty. Full lists are below. You can also find IDs dynamically by logging in to [online24.medicover.pl](https://online24.medicover.pl), opening your browser's developer tools (F12 → Network tab), and inspecting the outgoing appointment search API request.

### Regions

| ID       | Name                    |
| -------- | ----------------------- |
| `102426` | Białystok               |
| `104450` | Bielsko-Biała           |
| `102424` | Bydgoszcz               |
| `115682` | Częstochowa             |
| `114060` | Elbląg                  |
| `102200` | Gliwice                 |
| `116902` | Inowrocław              |
| `203`    | Katowice                |
| `109674` | Kielce                  |
| `104720` | Kostrzyn n/Odrą         |
| `202`    | Kraków                  |
| `113854` | Kwidzyn                 |
| `117524` | Leszno                  |
| `199`    | Łódź                    |
| `100032` | Lublin                  |
| `121380` | Network Telemedycyna    |
| `117526` | Olsztyn                 |
| `117`    | Płock                   |
| `207`    | Poznań                  |
| `121814` | Rzeszów                 |
| `253`    | Słupsk                  |
| `110338` | Sosnowiec               |
| `206`    | Szczecin                |
| `105814` | e-wizyta                |
| `117528` | Toruń                   |
| `200`    | Trójmiasto              |
| `204`    | Warszawa                |
| `205`    | Wrocław                 |

### Specialties

| ID      | Name                                                                 |
| ------- | -------------------------------------------------------------------- |
| `16234` | Medicover Express - przeziębienie, grypa                             |
| `56386` | Medicover Express - przeziębienie, grypa - porada tel. zdalna        |
| `55522` | Medicover Express - przeziębienie, grypa - porada telefoniczna       |
| `12500` | Alergolog - czat                                                     |
| `176`   | Alergolog dorośli                                                    |
| `44062` | Alergolog dorośli - porada telefoniczna                              |
| `49298` | Alergolog dorośli - porada telefoniczna zdalna                       |
| `178`   | Alergolog dorośli odczulanie                                         |
| `8168`  | Angiolog                                                             |
| `11682` | Badanie dna oka - dorośli                                            |
| `2`     | Chirurg dorośli                                                      |
| `44252` | Chirurg dorośli - porada telefoniczna                                |
| `78`    | Chirurg naczyniowy                                                   |
| `44256` | Chirurg naczyniowy - porada telefoniczna                             |
| `28760` | Chirurg stomatolog - leczenie                                        |
| `27952` | Chirurgia - zdjęcie szwów                                            |
| `5346`  | Chirurgia - zmiana opatrunku                                         |
| `1190`  | Choroby zakaźne dorośli                                              |
| `44258` | Choroby zakaźne dorośli - porada telefoniczna                        |
| `6254`  | Cytologia                                                            |
| `12288` | Dermatolog - czat                                                    |
| `3`     | Dermatolog dorośli                                                   |
| `69362` | Dermatolog dorośli - kurzajki - konsultacja                          |
| `43852` | Dermatolog dorośli - porada telefoniczna                             |
| `99`    | Diabetolog                                                           |
| `29178` | Diabetolog - porada telefoniczna                                     |
| `49318` | Diabetolog dorośli - porada telefoniczna zdalna                      |
| `25104` | Dietetyk - porada telefoniczna                                       |
| `182`   | Dietetyk dorośli                                                     |
| `28764` | Endodonta - leczenie                                                 |
| `83012` | Endodonta - wizyta konsultacyjna                                     |
| `12088` | Endokrynolog - czat                                                  |
| `5`     | Endokrynolog dorośli                                                 |
| `27962` | Endokrynolog dorośli - porada telefoniczna                           |
| `49322` | Endokrynolog dorośli - porada telefoniczna zdalna                    |
| `48080` | Fizjoterapia stomatologiczna - leczenie                              |
| `42`    | Gastroenterolog dorośli                                              |
| `44054` | Gastroenterolog dorośli - porada telefoniczna                        |
| `49326` | Gastroenterolog dorośli - porada telefoniczna zdalna                 |
| `32818` | Ginekolog - porada telefoniczna                                      |
| `49330` | Ginekolog - porada telefoniczna zdalna                               |
| `4800`  | Ginekolog - prowadzenie ciąży                                        |
| `44266` | Ginekolog - prowadzenie ciąży - porada telefoniczna                  |
| `49332` | Ginekolog - prowadzenie ciąży - porada telefoniczna zdalna           |
| `4798`  | Ginekolog dorośli                                                    |
| `32`    | Ginekolog Endokrynolog dorośli                                       |
| `44270` | Ginekolog Endokrynolog dorośli - porada telefoniczna                 |
| `94448` | Ginekologia - awaryjna antykoncepcja - porada tel. u położnej        |
| `46068` | Ginekologia - infekcja intymna u położnej                            |
| `10244` | Ginekologia - pobranie wymazu                                        |
| `57924` | Ginekologia - potwierdzenie ciąży u położnej - porada telefoniczna   |
| `72380` | Ginekologia - przygotowanie do ciąży u położnej                      |
| `53`    | Hematolog                                                            |
| `44272` | Hematolog dorośli - porada telefoniczna                              |
| `49338` | Hematolog dorośli - porada telefoniczna zdalna                       |
| `54`    | Hepatolog                                                            |
| `44276` | Hepatolog - porada telefoniczna                                      |
| `112`   | Higienistka stomatologiczna                                          |
| `77798` | Higienizacja premium 8w1                                             |
| `52706` | Immunolog dorośli                                                    |
| `54912` | Immunolog dorośli - porada telefoniczna                              |
| `29394` | Implantolog - leczenie                                               |
| `9`     | Internista                                                           |
| `10212` | Internista - czat                                                    |
| `19046` | Internista - porada telefoniczna                                     |
| `49344` | Internista - porada telefoniczna zdalna                              |
| `5030`  | Internista - szczepienie                                             |
| `7338`  | Internista dyżurny                                                   |
| `39836` | Invisalign - leczenie                                                |
| `10`    | Kardiolog dorośli                                                    |
| `43652` | Kardiolog dorośli - porada telefoniczna                              |
| `72984` | Konsultacja stylisty                                                 |
| `87430` | Kwalifikacja i szczepienie - pielęgniarka                            |
| `192`   | Laryngolog dorośli                                                   |
| `44066` | Laryngolog dorośli - porada telefoniczna                             |
| `85830` | Laryngologia - płukanie ucha u pielęgniarki                          |
| `7344`  | Lekarz dyżurny medycyny rodzinnej - dorośli                          |
| `96`    | Logopeda dorośli                                                     |
| `48082` | Logopedia stomatologiczna                                            |
| `16236` | Medicover Express - szczepienia dorośli                              |
| `486`   | Medicover Express - szczepienia grypa                                |
| `62742` | Medicover Express - szczepienia grypa - dorośli - pielęgniarka       |
| `70770` | Medicover Express - wymrażanie kurzajek                              |
| `55920` | Medycyna estetyczna twarzy i szyi                                    |
| `149`   | Medycyna podróży                                                     |
| `12504` | Medycyna podróży - czat                                              |
| `9976`  | Medycyna podróży - dorośli                                           |
| `44278` | Medycyna podróży - dorośli - porada telefoniczna                     |
| `49354` | Medycyna podróży - dorośli - porada telefoniczna zdalna              |
| `1586`  | Medycyna Rodzinna - dorośli                                          |
| `27964` | Medycyna rodzinna - dorośli - porada telefoniczna                    |
| `49358` | Medycyna rodzinna - dorośli - porada telefoniczna zdalna             |
| `27970` | Medycyna rodzinna - dzieci - porada telefoniczna                     |
| `19044` | Medycyna Rodzinna - porada telefoniczna                              |
| `9180`  | Medycyna Rodzinna - szczepienia (dorośli)                            |
| `1986`  | Medycyna Sportowa                                                    |
| `33`    | Nefrolog dorośli                                                     |
| `44070` | Nefrolog dorośli - porada telefoniczna                               |
| `80`    | Neurochirurg                                                         |
| `16`    | Neurolog dorośli                                                     |
| `44074` | Neurolog dorośli - porada telefoniczna                               |
| `198`   | Okulista dorośli                                                     |
| `44078` | Okulista dorośli - porada telefoniczna                               |
| `19054` | Okulistyka - badanie wzroku                                          |
| `76590` | Okulistyka - dobór okularów progresywnych                            |
| `22694` | Okulistyka - dobór soczewek kontaktowych                             |
| `58724` | Okulistyka - pakiet dobór okularów i soczewek kontaktowych           |
| `79`    | Onkolog dorośli                                                      |
| `44284` | Onkolog dorośli - porada telefoniczna                                |
| `50498` | Optometrysta - porada telefoniczna                                   |
| `28766` | Ortodonta - leczenie                                                 |
| `163`   | Ortopeda dorośli                                                     |
| `44058` | Ortopeda dorośli - porada telefoniczna                               |
| `49378` | Ortopeda dorośli - porada telefoniczna zdalna                        |
| `202`   | Ortopeda dorośli i dzieci                                            |
| `10210` | Pediatra - czat                                                      |
| `28768` | Periodontolog - leczenie                                             |
| `32196` | Pielęgniarka - analiza składu masy ciała                             |
| `95054` | Pielęgniarka - wizyta profilaktyczna                                 |
| `46872` | Pielęgniarka internistyczna - porada telefoniczna                    |
| `11882` | Położna - czat                                                       |
| `5832`  | Położna - porada telefoniczna                                        |
| `27158` | Poradnia Bólu Pleców i Układu Ruchu - dorośli                        |
| `20056` | Poradnia Leczenia Boreliozy                                          |
| `27160` | Poradnia Układu Ruchu - dzieci                                       |
| `56`    | Proktolog dorośli                                                    |
| `28770` | Protetyk - leczenie                                                  |
| `84418` | Protetyk - metamorfoza uśmiechu                                      |
| `38636` | Protetyk słuchu - dobór aparatu słuchowego                           |
| `63156` | Przeziębienie, grypa - pielęgniarka specjalistyczna                  |
| `24`    | Psychiatra dorośli                                                   |
| `48912` | Psychiatra dorośli - porada telefoniczna                             |
| `25`    | Psycholog dorośli                                                    |
| `48914` | Psycholog dorośli - porada telefoniczna                              |
| `173`   | Psycholog dziecięcy                                                  |
| `48918` | Psycholog dziecięcy - porada telefoniczna                            |
| `41`    | Pulmonolog dorośli                                                   |
| `44082` | Pulmonolog dorośli - porada telefoniczna                             |
| `49394` | Pulmonolog dorośli - porada telefoniczna zdalna                      |
| `52110` | Punkt Pobrań - ciężarne                                              |
| `89838` | Punkt Pobrań - ciężarne - Szczecin                                   |
| `52106` | Punkt Pobrań - dorośli                                               |
| `89836` | Punkt Pobrań - dorośli - Szczecin                                    |
| `52108` | Punkt Pobrań - dzieci                                                |
| `26`    | Reumatolog dorośli                                                   |
| `44086` | Reumatolog dorośli - porada telefoniczna                             |
| `23504` | Stomatolog - leczenie                                                |
| `22890` | Stomatolog - przegląd                                                |
| `28772` | Stomatolog dziecięcy - leczenie                                      |
| `85628` | Urolog - zabieg P-shot rewitalizacja prącia                          |
| `30`    | Urolog dorośli                                                       |
| `44290` | Urolog dorośli - porada telefoniczna                                 |
| `76798` | Urologia - pobranie wymazu u mężczyzn przez pielęgniarkę             |
| `55112` | Wizyta Pierwszorazowa z planem leczenia                              |

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
