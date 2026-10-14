
"""Safe JSON storage for CampusFlow audit events."""

import json
import os
import tempfile

from campusflow.storage import StorageError

DEFAULT_EVENTS_PATH = os.path.join("data", "events.json")


def save_events(events, path=DEFAULT_EVENTS_PATH):
    """Save audit events safely to a JSON file."""
    folder = os.path.dirname(path)

    if folder:
        os.makedirs(folder, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        dir=folder or ".",
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(events, file, indent=2)

        os.replace(temp_path, path)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def load_events(path=DEFAULT_EVENTS_PATH):
    """Load audit events. Return an empty list if the file is missing."""
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise StorageError(
            f"Event file '{path}' is invalid: {error}. "
            "The original file was not changed."
        ) from error

    if not isinstance(data, list) or not all(
        isinstance(event, dict) for event in data
    ):
        raise StorageError(
            f"Event file '{path}' must contain a list of events."
        )

    return data
