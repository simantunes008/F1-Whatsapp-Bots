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
├── posters/             # Race posters named by circuitId (e.g., zandvoort.jpg)
├── .env
├── .gitignore
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

### 2. Saturday Grid Bot (`grid_bot.py`)
* **Execution**: Automated via GitHub Actions (Every Saturday at 17:00 UTC).
* **Functionality**: Validates if qualifying is scheduled for the current day. Once official results are published by the API, it retrieves the starting grid, formats the top positions with drivers and constructors, sends the update to WhatsApp, and pins the message.

### 3. Live Race Bot (`live_bot.py`)
* **Execution**: Local execution during race sessions.
* **Prerequisites**: Active **F1TV Access, Pro, or Premium** subscription (required by FastF1 for live telemetry). Authentication is done via browser flow on first run and cached locally.
* **Functionality**: Connects to official F1 live timing servers using FastF1's SignalR client and streams events to `f1_live.txt`. A parallel log-tailing parser monitors the stream and sends instant alerts for:
  * **Track Status**: Safety Car, Red Flag, and Track Clear.
  * **Race Control**: Filtered real-time notifications for investigations and penalties.

## Environment Variables

Configure the following variables locally in a `.env` file or securely under GitHub Repository **Settings > Secrets and variables > Actions**:

* `ID_INSTANCE`: Your Green API instance ID.
* `API_TOKEN`: Your Green API token.
* `CHAT_ID`: The target WhatsApp group chat ID.

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