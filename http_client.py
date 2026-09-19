"""HTTP requests with timeouts and retries, shared by every bot.

A transient 500 from Jolpica or Green API used to lose the week's message:
the scheduled bots only run in short windows and get no second chance within
a single execution.
"""

import time

import requests

TIMEOUT = 10
ATTEMPTS = 3
BACKOFF_BASE = 3


class RequestFailed(Exception):
    """The request failed after all attempts were exhausted."""


def request(method, url, **kwargs):
    """Make an HTTP request, retrying on network errors and 5xx responses.

    4xx responses are returned without retrying: those are configuration
    errors (bad token, unknown chat) that will not improve on a second try.
    """
    kwargs.setdefault("timeout", TIMEOUT)
    last_error = None

    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code >= 500:
                raise requests.HTTPError(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
            return response
        except requests.RequestException as error:
            last_error = error
            if attempt < ATTEMPTS:
                delay = BACKOFF_BASE * attempt
                print(
                    f"Attempt {attempt}/{ATTEMPTS} failed ({error}). "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)

    raise RequestFailed(
        f"{method} {url} failed after {ATTEMPTS} attempts: {last_error}"
    )


def get_json(url, **kwargs):
    """GET returning the decoded JSON body."""
    response = request("GET", url, **kwargs)
    response.raise_for_status()
    return response.json()
