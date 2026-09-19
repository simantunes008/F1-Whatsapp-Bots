# F1 WhatsApp Automation Bot

A comprehensive Formula 1 notification system built with Python, Green API, Jolpica F1 API, and FastF1 that automates weekend schedules, starting grids, dynamic posters, and real-time race events directly to a WhatsApp group.

## Tech Stack

* **Language**: Python 3.10
* **Messaging Gateway**: Green API
* **Data Sources**: Jolpica F1 API & FastF1
* **Automation & CI/CD**: GitHub Actions

## Project Structure

```text
F1BOT/
├── .github/workflows/
│   ├── calendar_bot.yml
│   └── grid_bot.yml
├── tests/
│   ├── f1_live_sample.txt   # Trimmed real capture used as fixture
│   └── test_parser.py       # Live-timing parser tests
├── posters/             # Race posters named by circuitId (e.g., zandvoort.jpg)
├── .env
├── .gitignore
├── http_client.py       # Shared HTTP layer: timeouts + retries
├── whatsapp.py          # Green API client: send & pin
├── f1_api.py            # Jolpica F1 API client
├── calendar_bot.py
├── grid_bot.py
├── live_bot.py
├── requirements.txt
└── README.md
```

## System Components & Workflows

### 1. Monday Calendar Bot (`calendar_bot.py`)
* **Execution**: Automated via GitHub Actions (Every Monday at 09:00 UTC).
* **Functionality**: Fetches the next upcoming Grand Prix. If the race takes place within 7 days, it parses session timings (Practice, Sprint Qualifying, Sprint, Qualifying, Race), converts them to `Europe/Lisbon` time, attaches the circuit poster from the repo, sends a formatted message to WhatsApp, and pins it for everyone.

### 2. Grid Bot (`grid_bot.py`)
* **Execution**: Automated via GitHub Actions (hourly, Friday through Sunday).
* **Functionality**: Runs hourly and sends on the first execution where the API has published the qualifying results, then stays quiet for the rest of the weekend. The hourly schedule is required because qualifying times vary by many hours between Grands Prix, and on sprint weekends qualifying falls on Friday. The valid window is between the start of qualifying and the start of the race, computed in UTC.
* **Deduplication**: `.state/grid_enviados.json` records which rounds were already sent and is persisted between runs via `actions/cache`. If the cache expires, the worst case is a duplicate message rather than a missing one.

### 3. Live Race Bot (`live_bot.py`)
* **Execution**: Local execution during race sessions.
* **Prerequisites**: Active **F1TV Access, Pro, or Premium** subscription (required by FastF1 for live telemetry). Authentication is done via browser flow on first run and cached locally.
* **Functionality**: Connects to official F1 live timing servers using FastF1's SignalR client and streams events to `f1_live.txt`. A parallel log-tailing parser monitors the stream and sends instant alerts for:
  * **Track Status**: Safety Car, Virtual Safety Car, Red Flag, and Track Clear. Yellow flags are excluded on purpose, being too frequent to be useful in a group chat.
  * **Race Control**: Real-time notifications for investigations and penalties, excluding `NO FURTHER INVESTIGATION` rulings.
* **Reliability**: FastF1's client does not reconnect on its own, so it is wrapped in a reconnect loop. The history snapshot received on connection primes the internal state without alerting, so joining a session mid-race does not dump the backlog into the group. A previous capture of `f1_live.txt` is moved aside to `f1_live.prev.txt` on startup.

## Reliability

* All HTTP calls go through `http_client.py`, which applies a 10-second timeout and retries three times on network errors and 5xx responses. A `4xx` is not retried: it signals a configuration problem.
* The scheduled bots exit with status `0` when there is nothing to send and status `1` on error, so a failed GitHub Actions run is visible and triggers a notification instead of passing silently as green.

## Environment Variables

Configure the following variables locally in a `.env` file or securely under GitHub Repository **Settings > Secrets and variables > Actions**:

* `ID_INSTANCE`: Your Green API instance ID.
* `API_TOKEN`: Your Green API token.
* `CHAT_ID`: The target WhatsApp group chat ID.
* `GREEN_API_HOST` *(optional)*: Overrides the Green API host, whose prefix is tied to the instance.

> **Note**: `load_dotenv()` resolves `.env` relative to `whatsapp.py`, not the working directory. Running any bot by hand sends real messages to the group, even with the environment variables cleared.

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/simantunes008/F1-Whatsapp-Bots.git](https://github.com/simantunes008/F1-Whatsapp-Bots.git)
   cd F1-Whatsapp-Bots
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the live bot locally:
   ```bash
   python live_bot.py
   ```

## Tests

```bash
python tests/test_parser.py
```

Covers the live-timing parser against a trimmed real capture. The format of
`f1_live.txt` is defined by F1 and FastF1 rather than by this project, so it
can change without notice — and when it did, the bot silently stopped sending
alerts. Nothing is sent while the tests run; `whatsapp.enviar` is replaced by
a collector.

Run this after touching `live_bot.py`. To refresh the fixture, capture a new
session and trim it to the topics under test.