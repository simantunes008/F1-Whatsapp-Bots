"""Green API client: sending and pinning messages in the group.

This block used to be copied across all three bots. Any change to the host,
the credentials or the send/pin sequence now happens in one place.

Note: message bodies stay in Portuguese — they are what the group reads.
"""

import os

from dotenv import load_dotenv

from http_client import RequestFailed, request

load_dotenv()

ID_INSTANCE = os.getenv("ID_INSTANCE")
API_TOKEN = os.getenv("API_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# The host prefix is tied to the Green API instance, it is not a generic
# endpoint. GREEN_API_HOST allows switching instances without code changes.
HOST = os.getenv("GREEN_API_HOST", "https://7107.api.greenapi.com")


class WhatsAppError(Exception):
    """Green API rejected the request, or configuration is missing."""


def validate_config():
    """Fail early and by name, instead of an opaque 401 mid-send."""
    missing = [
        name
        for name, value in (
            ("ID_INSTANCE", ID_INSTANCE),
            ("API_TOKEN", API_TOKEN),
            ("CHAT_ID", CHAT_ID),
        )
        if not value
    ]
    if missing:
        raise WhatsAppError(f"Missing environment variables: {', '.join(missing)}")


def _url(api_method):
    return f"{HOST}/waInstance{ID_INSTANCE}/{api_method}/{API_TOKEN}"


def send(message):
    """Send the message and return its idMessage.

    Raises WhatsAppError if the send is not confirmed: the caller decides
    whether that ends the program or is merely logged.
    """
    validate_config()
    response = request(
        "POST", _url("sendMessage"), json={"chatId": CHAT_ID, "message": message}
    )

    if response.status_code != 200:
        raise WhatsAppError(
            f"Send rejected (HTTP {response.status_code}): {response.text[:200]}"
        )

    message_id = response.json().get("idMessage")
    if not message_id:
        raise WhatsAppError(f"Response without idMessage: {response.text[:200]}")

    return message_id


def pin(message_id):
    """Pin the message for everyone. A failure here warns but does not
    propagate: the message already reached the group, which is what counts."""
    try:
        response = request(
            "POST",
            _url("pinMessage"),
            json={
                "chatId": CHAT_ID,
                "idMessage": message_id,
                "pin": True,
                "pinType": "pinForEveryone",
            },
        )
    except RequestFailed as error:
        print(f"Warning: could not pin the message: {error}")
        return False

    if response.status_code != 200:
        print(f"Warning: could not pin the message: {response.text[:200]}")
        return False

    print("Message pinned in the group.")
    return True


def send_and_pin(message):
    """Send and pin. Returns the idMessage."""
    message_id = send(message)
    print("Message sent.")
    pin(message_id)
    return message_id
