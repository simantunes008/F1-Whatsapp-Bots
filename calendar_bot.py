"""Send the Grand Prix weekend schedule to the WhatsApp group.

Exits 0 when there is nothing to send and 1 on error, so that GitHub Actions
marks the run as failed and notifies. Previously any failure was hidden
inside a green job.

Message text stays in Portuguese: it is what the group reads.
"""

import sys
import zoneinfo
from datetime import datetime, timezone

import f1_api
import whatsapp

LISBON = zoneinfo.ZoneInfo("Europe/Lisbon")
WINDOW_DAYS = 7
STREAM_LINK = "https://formula1streams.plus/"


def format_time(date_str, time_str):
    """Convert a UTC date and time from the API into Lisbon local time."""
    utc = datetime.strptime(
        f"{date_str}T{time_str}", "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    return utc.astimezone(LISBON).strftime("%d/%m (%H:%M)")


def session_line(race, key, label):
    """Formatted line for one session, or empty if the weekend lacks it."""
    session = race.get(key)
    if not session:
        return ""
    return f"*{label}:* {format_time(session['date'], session['time'])}\n"


def build_message(race):
    message = f"*{race['raceName']}*\n\n"
    message += session_line(race, "FirstPractice", "Treino 1")

    # On a sprint weekend the sprint sessions take the place of FP2/FP3.
    if "SprintQualifying" in race:
        message += session_line(race, "SprintQualifying", "Qualificação Sprint")
    else:
        message += session_line(race, "SecondPractice", "Treino 2")

    if "Sprint" in race:
        message += session_line(race, "Sprint", "Sprint")
    else:
        message += session_line(race, "ThirdPractice", "Treino 3")

    message += session_line(race, "Qualifying", "Qualificação")
    message += f"*Corrida:* {format_time(race['date'], race['time'])}\n\n"
    message += f"*Assiste em:* {STREAM_LINK}"
    return message


def main():
    whatsapp.validate_config()

    race = f1_api.next_race()
    race_date = datetime.strptime(race["date"], "%Y-%m-%d").date()
    days = (race_date - datetime.now(LISBON).date()).days

    if not 0 <= days <= WINDOW_DAYS:
        print(f"Next race ({race['raceName']}) is {days} days away. Nothing to send.")
        return 0

    whatsapp.send_and_pin(build_message(race))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
