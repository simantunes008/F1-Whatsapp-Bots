"""Access to the Jolpica F1 API (Ergast-compatible)."""

from http_client import get_json

BASE = "https://api.jolpi.ca/ergast/f1"


class NoData(Exception):
    """The API responded, but without the requested data."""


def next_race():
    """Return the next race of the current calendar."""
    data = get_json(f"{BASE}/current/next.json")
    races = data["MRData"]["RaceTable"]["Races"]
    if not races:
        raise NoData("The API returned no upcoming race.")
    return races[0]


def qualifying_results(season, round_number):
    """Return the QualifyingResults, or None if they are not published yet.

    The distinction matters: None is a normal situation (qualifying has just
    finished) and must not be treated as an error.
    """
    data = get_json(f"{BASE}/{season}/{round_number}/qualifying.json")
    races = data["MRData"]["RaceTable"]["Races"]
    if not races or "QualifyingResults" not in races[0]:
        return None
    return races[0]["QualifyingResults"]
