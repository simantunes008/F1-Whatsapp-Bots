"""Tests for the live_bot parser against a real F1 capture.

The format of f1_live.txt is defined by F1 and FastF1, not by this project:
it can change without notice and, when it did, the bot silently stopped
sending alerts. That is the risk these tests cover.

Run with:  python3 tests/test_parser.py
"""

import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import live_bot  # noqa: E402

# Before anything else: importing whatsapp loads the project's .env, so any
# call to send() would push a real message to the group. Here we only collect
# what would have been sent.
SENT = []
live_bot.whatsapp.send = SENT.append

FIXTURE = Path(__file__).parent / "f1_live_sample.txt"


def fixture_lines():
    return FIXTURE.read_text(encoding="utf-8").splitlines()


def record(wanted_topic):
    for line in fixture_lines():
        topic, data = live_bot.parse_line(line)
        if topic == wanted_topic:
            return data
    raise AssertionError(f"{wanted_topic} is not in the fixture")


def incremental(topic, data):
    """Reproduce a live update: FastF1 writes the payload as a dict, unlike
    the initial snapshot, which writes it as a JSON string."""
    return str([topic, data, "2026-09-13T13:00:00.000Z"])


def test_whole_capture_is_readable():
    topics = [live_bot.parse_line(l)[0] for l in fixture_lines()]
    assert None not in topics, "there are real lines the parser cannot read"
    assert {"TrackStatus", "RaceControlMessages"} <= set(topics)


def test_snapshot_does_not_alert_retroactively():
    """Connecting mid-session must not dump the history into the group."""
    SENT.clear()
    live_bot.handle_track_status(record("TrackStatus"), None, True)
    live_bot.handle_race_control(record("RaceControlMessages"), set(), True)
    assert SENT == [], SENT


def test_track_status_transitions():
    SENT.clear()
    status = "1"
    for code in ("4", "4", "2", "6", "5", "1"):
        topic, data = live_bot.parse_line(incremental("TrackStatus", {"Status": code}))
        assert topic == "TrackStatus"
        status = live_bot.handle_track_status(data, status)

    # The repeated 4 does not re-alert and yellow (2) is ignored on purpose.
    assert SENT == [
        "*SAFETY CAR NA PISTA!*",
        "*VIRTUAL SAFETY CAR!*",
        "*BANDEIRA VERMELHA!* Sessão interrompida.",
        "*PISTA LIMPA!* Corrida retomada.",
    ], SENT


def test_race_control_filters_what_matters():
    SENT.clear()
    seen = set()
    messages = record("RaceControlMessages")["Messages"]
    # In live updates Messages arrives as a dict keyed by index, not a list.
    topic, data = live_bot.parse_line(
        incremental("RaceControlMessages",
                    {"Messages": {str(i): m for i, m in enumerate(messages)}})
    )
    assert topic == "RaceControlMessages"
    live_bot.handle_race_control(data, seen)
    live_bot.handle_race_control(data, seen)  # repeated must not re-alert

    assert len(SENT) == 2, SENT
    assert SENT[0].startswith("*Investigação:*")
    assert SENT[1].startswith("*Penalização:*")
    # "REVIEWED NO FURTHER INVESTIGATION" contains INVESTIGATION but must not alert.
    assert not any("NO FURTHER" in m for m in SENT), SENT


def test_invalid_lines_do_not_crash():
    for junk in ("", "   ", "junk\n", "[incomplete",
                 "['Topic', 'not-json', '']", "['Topic', 42, '']"):
        assert live_bot.parse_line(junk) == (None, None), repr(junk)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            # Alerts print to stdout; only the verdict matters here.
            with contextlib.redirect_stdout(io.StringIO()):
                test()
            print(f"  PASS  {test.__name__}")
        except AssertionError as error:
            failures += 1
            print(f"  FAIL  {test.__name__}: {error}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    sys.exit(1 if failures else 0)
