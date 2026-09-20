"""Live alerts during an F1 session.

Two halves: a daemon thread runs FastF1's SignalRClient, which writes the raw
messages to f1_live.txt; the main thread tails that file and sends alerts.
The file is the only channel between them.

Requires an F1TV subscription: FastF1 authenticates on startup (browser flow
the first time, cached token afterwards).

File format: FastF1 writes str([topic, data, timestamp]) — a Python literal,
not JSON. In the initial snapshot 'data' is a JSON string; in incremental
updates it is already a dict. That is why reading goes through
ast.literal_eval rather than json.loads over the whole line.

Alert text stays in Portuguese: it is what the group reads.
"""

import ast
import json
import os
import sys
import threading
import time
from pathlib import Path

from fastf1.livetiming.client import SignalRClient

import whatsapp

DATA_FILE = Path("f1_live.txt")
PREVIOUS_FILE = Path("f1_live.prev.txt")

# F1 TrackStatus codes. Yellow (2) is deliberately left out: during a race it
# is far too frequent and would flood the group. So is VSC ending (7),
# because AllClear (1) always follows it.
TRACK_STATUS_ALERTS = {
    "1": "*PISTA LIMPA!* Corrida retomada.",
    "4": "*SAFETY CAR NA PISTA!*",
    "5": "*BANDEIRA VERMELHA!* Sessão interrompida.",
    "6": "*VIRTUAL SAFETY CAR!*",
}

RACE_CONTROL_FILTERS = (
    ("INVESTIGATION", "Investigação"),
    ("PENALTY", "Penalização"),
)

# "REVIEWED NO FURTHER INVESTIGATION" contains "INVESTIGATION" but means the
# exact opposite: the case was looked at and closed with no consequences.
RACE_CONTROL_EXCLUSIONS = ("NO FURTHER INVESTIGATION",)

READ_INTERVAL = 1
RECONNECT_DELAY = 15
STARTUP_TIMEOUT = 120
# SignalRClient shuts itself down after `timeout` seconds without data. The
# default (60s) kills the connection while waiting for a session to start,
# so it is widened here.
CLIENT_TIMEOUT = int(os.getenv("FASTF1_TIMEOUT", "600"))
STALL_WARNING = 300
# Consecutive client failures before giving up during startup. Two is enough
# to tell a bad token from a blip, and reports in ~30s instead of waiting out
# STARTUP_TIMEOUT.
STARTUP_FAILURES_ALLOWED = 2


def rotate_capture():
    """Move a previous capture aside before starting.

    The client writes in append mode (see run_client), so without this every
    session would pile into the same file: it would grow without bound and
    stop being usable with FastF1's LiveTimingData, which expects one session
    at a time.

    It moves rather than deletes because the previous capture is the only
    real data available for validating parser changes — it is where
    tests/f1_live_sample.txt came from. Only one generation is kept.
    """
    if DATA_FILE.exists():
        DATA_FILE.replace(PREVIOUS_FILE)
        print(f"Previous capture saved to {PREVIOUS_FILE}.")


def send_alert(message):
    """A failed alert must not bring down the monitor mid-race."""
    print(f"ALERT: {message}")
    try:
        whatsapp.send(message)
    except Exception as error:
        print(f"ERROR sending alert: {error}", file=sys.stderr)


def parse_line(line):
    """Return (topic, data) for a raw line, or (None, None) if unreadable."""
    line = line.strip()
    if not line.startswith("["):
        return None, None

    try:
        record = ast.literal_eval(line)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None, None

    if not isinstance(record, list) or len(record) < 2:
        return None, None

    topic, data = record[0], record[1]
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None, None

    if not isinstance(data, dict):
        return None, None
    return topic, data


def handle_track_status(data, previous_status, quiet=False):
    """Alert when the track status changes. Returns the new status."""
    status = data.get("Status")
    if status is None or status == previous_status:
        return previous_status

    if not quiet:
        alert = TRACK_STATUS_ALERTS.get(str(status))
        if alert:
            send_alert(alert)
    return status


def handle_race_control(data, seen, quiet=False):
    messages = data.get("Messages", [])
    # In the initial snapshot 'Messages' is a list; in incremental updates it
    # arrives as a dict keyed by index.
    if isinstance(messages, dict):
        messages = list(messages.values())

    for message in messages:
        if not isinstance(message, dict):
            continue
        text = (message.get("Message") or "").strip()
        if not text or text in seen:
            continue

        # On the initial snapshot, just record it: alerting would replay what
        # happened before the bot connected.
        if quiet:
            seen.add(text)
            continue

        upper = text.upper()
        if any(exclusion in upper for exclusion in RACE_CONTROL_EXCLUSIONS):
            seen.add(text)
            continue

        for pattern, label in RACE_CONTROL_FILTERS:
            if pattern in upper:
                send_alert(f"*{label}:* {text}")
                seen.add(text)
                break


class ClientStatus:
    """What the client thread reports back to the monitor.

    The thread retries forever, so it never dies and its health cannot be
    inferred from `Thread.is_alive()`. Failures have to be published here
    instead.
    """

    def __init__(self):
        self.failures = 0
        self.last_error = None

    def record_failure(self, error):
        self.failures += 1
        self.last_error = error

    def record_success(self):
        self.failures = 0


def run_client(status):
    """Keep the connection alive: FastF1's SignalRClient does not reconnect.

    Opens in 'a' mode so that a reconnect cannot truncate what was already
    written and desynchronize the monitor.
    """
    attempt = 0
    while True:
        attempt += 1
        print(f"Connecting to the F1 servers (attempt {attempt})...")
        try:
            SignalRClient(
                str(DATA_FILE), filemode="a", timeout=CLIENT_TIMEOUT
            ).start()
            status.record_success()
            print("Connection closed by the server.", file=sys.stderr)
        except Exception as error:
            status.record_failure(error)
            print(f"ERROR in the FastF1 client: {error}", file=sys.stderr)
        print(f"Reconnecting in {RECONNECT_DELAY}s...")
        time.sleep(RECONNECT_DELAY)


def wait_for_file(status):
    deadline = time.time() + STARTUP_TIMEOUT
    while not DATA_FILE.exists():
        if status.failures >= STARTUP_FAILURES_ALLOWED:
            raise RuntimeError(
                f"The FastF1 client failed {status.failures} times in a row: "
                f"{status.last_error}. Check the F1TV authentication."
            )
        if time.time() > deadline:
            raise RuntimeError(
                f"{DATA_FILE} did not appear within {STARTUP_TIMEOUT}s, and "
                "the client reported no error. The session may not be live."
            )
        time.sleep(1)


def follow_file(status):
    """Tail the file line by line and fire the alerts."""
    track_status = None
    seen = set()
    topics_seen = set()
    partial = ""
    last_data = time.time()
    last_warning = 0.0

    with DATA_FILE.open("r", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)

        while True:
            chunk = handle.readline()

            if not chunk:
                now = time.time()
                if (now - last_data > STALL_WARNING
                        and now - last_warning > STALL_WARNING):
                    minutes = int((now - last_data) // 60)
                    detail = (
                        f" Last client error: {status.last_error}"
                        if status.failures else ""
                    )
                    print(
                        f"Warning: no new data for {minutes} minutes. "
                        f"The session may have ended or the connection "
                        f"dropped.{detail}",
                        file=sys.stderr,
                    )
                    last_warning = now

                time.sleep(READ_INTERVAL)
                continue

            # readline() can return a line that is still being written.
            partial += chunk
            if not partial.endswith("\n"):
                continue
            line, partial = partial, ""

            last_data = time.time()

            topic, data = parse_line(line)
            if topic is None:
                continue

            # The first record of each topic is the snapshot holding the
            # session history up to connection time. It primes the state; it
            # must not alert retroactively.
            snapshot = topic not in topics_seen
            topics_seen.add(topic)

            if topic == "TrackStatus":
                track_status = handle_track_status(data, track_status, snapshot)
            elif topic == "RaceControlMessages":
                handle_race_control(data, seen, snapshot)


def main():
    whatsapp.validate_config()
    rotate_capture()

    status = ClientStatus()
    threading.Thread(target=run_client, args=(status,), daemon=True).start()

    print("Waiting for data from FastF1...")
    wait_for_file(status)

    print("Monitoring the session. Ctrl+C to stop.")
    return follow_file(status)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
