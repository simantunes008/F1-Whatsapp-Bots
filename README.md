# F1 WhatsApp Automation Bot

An automated system built with Python, Green API, and the Jolpica F1 API that delivers Formula 1 race weekend schedules and starting grids directly to a WhatsApp group via GitHub Actions.

## Tech Stack

* **Language**: Python 3.10
* **Messaging Gateway**: Green API
* **Data Source**: Jolpica F1 API
* **Automation & CI/CD**: GitHub Actions

## Automated Workflows

### 1. Monday Calendar Bot (`f1_callender_bot.py`)
* **Schedule**: Runs every Monday at 09:00 UTC (10:00 Lisbon time).
* **Functionality**: Fetches the next upcoming Grand Prix. If the race takes place within the next 7 days, it formats all session schedules (Practice, Sprint, Qualifying, and Race) converted to `Europe/Lisbon` time, sends the message to WhatsApp, and pins it for everyone.

### 2. Saturday Grid Bot (`f1_grid_bot.py`)
* **Schedule**: Runs every Saturday at 17:00 UTC (18:00 Lisbon time).
* **Functionality**: Validates if today is a qualifying day for the current weekend. Once official results are published by the API, it retrieves the starting grid, formats the top positions with driver names and constructors, sends the update to WhatsApp, and pins the message.

## Environment Variables

To run the project locally or via GitHub Actions, configure the following secrets/variables:

* `ID_INSTANCE`: Your Green API instance ID.
* `API_TOKEN`: Your Green API token.
* `CHAT_ID`: The target WhatsApp group chat ID.

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/F1Bot.git](https://github.com/your-username/F1Bot.git)
   cd F1Bot