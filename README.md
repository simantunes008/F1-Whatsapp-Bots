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
│   ├── f1_live_sample.txt
│   └── test_parser.py
├── posters/             # Race posters named by circuitId (e.g., zandvoort.jpg)
├── .env
├── .gitignore
├── http_client.py       # Shared HTTP layer: timeouts + retries
├── whatsapp.py          # Green API client: send & pin
├── f1_api.py            # Jolpica F1 API client
├── calendar_bot.py
├── grid_bot.py
├── live_bot.py
├── requirements.txt         # Everything, for local development
├── requirements-ci.txt      # Scheduled bots only (no fastf1)
└── README.md
```

## System Components & Workflows

### 1. Monday Calendar Bot (`calendar_bot.py`)
* **Execution**: Automated via GitHub Actions (Every Monday at 09:17 UTC).
* **Functionality**: Fetches the next upcoming Grand Prix. If the race takes place within 7 days, it parses session timings (Practice, Sprint Qualifying, Sprint, Qualifying, Race), converts them to `Europe/Lisbon` time, attaches the circuit poster from the repo, sends a formatted message to WhatsApp, and pins it for everyone.

### 2. Grid Bot (`grid_bot.py`)
* **Execution**: Automated via GitHub Actions (hourly, Friday through Sunday).
* **Functionality**: Runs hourly and sends on the first execution where the API has published the qualifying results, then stays quiet for the rest of the weekend. The hourly schedule is required because qualifying times vary by many hours between Grands Prix, and on sprint weekends qualifying falls on Friday. The valid window is between the start of qualifying and the start of the race, computed in UTC.

### 3. Live Race Bot (`live_bot.py`)
* **Execution**: Local execution during race sessions.
* **Prerequisites**: Active **F1TV Access, Pro, or Premium** subscription (required by FastF1 for live telemetry). Authentication is done via browser flow on first run and cached locally.
* **Functionality**: Connects to official F1 live timing servers using FastF1's SignalR client and streams events to `f1_live.txt`. A parallel log-tailing parser monitors the stream and sends instant alerts for:
  * **Track Status**: Safety Car, Virtual Safety Car, Red Flag, and Track Clear. Yellow flags are excluded on purpose, being too frequent to be useful in a group chat.
  * **Race Control**: Real-time notifications for investigations and penalties, excluding `NO FURTHER INVESTIGATION` rulings.

## Environment Variables

Configure the following variables locally in a `.env` file or securely under GitHub Repository **Settings > Secrets and variables > Actions**:

* `ID_INSTANCE`: Your Green API instance ID.
* `API_TOKEN`: Your Green API token.
* `CHAT_ID`: The target WhatsApp group chat ID.
* `GREEN_API_HOST` *(optional)*: Overrides the Green API host, whose prefix is tied to the instance.

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

   The GitHub Actions workflows install `requirements-ci.txt` instead, which
   omits FastF1: only the live bot needs it, and the live bot never runs in
   CI. Pulling in pandas and numpy was taking 26 of every scheduled run's 31
   seconds.

3. Run the live bot locally:
   ```bash
   python live_bot.py
   ```

## Tests

```bash
python tests/test_parser.py
```
