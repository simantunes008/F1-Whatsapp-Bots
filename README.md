# F1 WhatsApp Automation Bot

A comprehensive Formula 1 notification system built with Python, Green API, Jolpica F1 API, and FastF1 that automates weekend schedules, starting grids, and real-time race events directly to a WhatsApp group.

## Tech Stack

* **Language**: Python 3.10
* **Messaging Gateway**: Green API
* **Data Sources**: Jolpica F1 API & FastF1
* **Automation & CI/CD**: GitHub Actions

## System Components & Workflows

### 1. Monday Calendar Bot (`callender_bot.py`)
* **Execution**: Automated via GitHub Actions (Every Monday at 09:00 UTC).
* **Functionality**: Fetches the next upcoming Grand Prix. If the race takes place within 7 days, it parses session timings (Practice, Sprint, Qualifying, Race), converts them to `Europe/Lisbon` time, sends a structured message to WhatsApp, and pins it for everyone.

### 2. Saturday Grid Bot (`grid_bot.py`)
* **Execution**: Automated via GitHub Actions (Every Saturday at 17:00 UTC).
* **Functionality**: Validates if qualifying is scheduled for the current day. Once official results are published by the API, it retrieves the starting grid, formats the top positions with drivers and constructors, sends the update to WhatsApp, and pins the message.

### 3. Live Race Bot (`live_bot.py`)
* **Execution**: Local execution during race sessions.
* **Functionality**: Connects to official F1 live timing servers using FastF1's SignalR client (`f1_live.txt`). It monitors real-time events and sends instant alerts to WhatsApp for:
  * **Track Status**: Safety Car ($\text{Status 4}$), Red Flag ($\text{Status 5}$), and Track Clear ($\text{Status 1}$).
  * **Race Control**: Detailed text notifications for investigations and penalties.

## Environment Variables

Configure the following variables locally in a `.env` file or securely under GitHub Repository **Settings > Secrets and variables > Actions**:

* `ID_INSTANCE`: Your Green API instance ID.
* `API_TOKEN`: Your Green API token.
* `CHAT_ID`: The target WhatsApp group chat ID (e.g., `120363424796569912@g.us`).

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/F1Bot.git](https://github.com/your-username/F1Bot.git)
   cd F1Bot