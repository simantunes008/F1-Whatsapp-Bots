"""Send the starting grid as soon as the qualifying results are published.

Runs hourly from Friday to Sunday (see .github/workflows/grid_bot.yml) and
sends on the first run where the API has results. Previously there was a
single attempt on Saturday at 17:00 UTC: if results were not published yet,
that weekend's grid was never sent, and on sprint weekends (qualifying on
Friday) it never ran on the right day at all.

The valid window is between the start of qualifying and the start of the
race, in UTC. Comparing the API's UTC date against a Lisbon date broke for
late-night sessions, where the two dates differ.

The state file prevents repeat sends on later runs of the same round. If the
state is lost (expired Actions cache), the worst case is a duplicate message,
not a missing one.

Message text stays in Portuguese: it is what the group reads.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import f1_api
import whatsapp

POSITIONS = 10
STATE_FILE = Path(os.getenv("GRID_STATE_FILE", ".state/grid_sent.json"))
ROUNDS_KEPT = 5


def _read_state():
    if not STATE_FILE.exists():
        return []
    try:
        sent = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        print(f"Warning: unreadable state ({error}). Treating it as empty.")
        return []
    return sent if isinstance(sent, list) else []


def already_sent(key):
    return key in _read_state()


def mark_sent(key):
    """Written after the send, deliberately: risking a duplicate beats
    marking as sent a grid that never reached the group."""
    sent = [*_read_state(), key][-ROUNDS_KEPT:]
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sent), encoding="utf-8")


def utc_instant(session, default_time):
    """Convert the API's {'date', 'time'} into a UTC datetime.

    Not every session carries 'time'. The default chosen by the caller widens
    the window rather than closing it: better to try once too often and fail
    at the next step than to skip a send.
    """
    time_str = session.get("time") or default_time
    return datetime.strptime(
        f"{session['date']}T{time_str}", "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)


def build_message(race_name, results):
    message = f"*Grelha de Partida - {race_name}*\n\n"
    for result in results[:POSITIONS]:
        driver = f"{result['Driver']['givenName']} {result['Driver']['familyName']}"
        message += f"{result['position']}. {driver} ({result['Constructor']['name']})\n"
    return message


def main():
    whatsapp.validate_config()

    race = f1_api.next_race()
    name = race["raceName"]

    if "Qualifying" not in race:
        print(f"{name} has no structured qualifying in the API. Nothing to do.")
        return 0

    qualifying_start = utc_instant(race["Qualifying"], "00:00:00Z")
    race_start = utc_instant(race, "23:59:59Z")
    now = datetime.now(timezone.utc)

    if now < qualifying_start:
        print(f"Qualifying for {name} starts at {qualifying_start:%d/%m %H:%M} UTC.")
        return 0

    if now >= race_start:
        print(f"{name} has already started. Outside the sending window.")
        return 0

    key = f"{race['season']}-{race['round']}"
    if already_sent(key):
        print(f"The grid for {name} ({key}) was already sent. Nothing to do.")
        return 0

    results = f1_api.qualifying_results(race["season"], race["round"])
    if not results:
        print("Results not published by the API yet. Will retry on the next run.")
        return 0

    whatsapp.send_and_pin(build_message(name, results))
    mark_sent(key)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
