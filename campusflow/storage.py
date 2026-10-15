import json
import os
import tempfile

DEFAULT_PATH = os.path.join("data", "tickets.json")


class StorageError(Exception):
    """Raised when the ticket file cannot be read safely."""


def save_tickets(tickets, path=DEFAULT_PATH):
    """Write the ticket list to a JSON file.

    Writes to a temporary file first, then swaps it in, so a crash
    while saving never leaves a half-written tickets file.
    """
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=folder or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2)
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def load_tickets(path=DEFAULT_PATH):
    """Read tickets from a JSON file.

    Missing file -> empty list (fresh start).
    Malformed or wrongly shaped file -> StorageError (never overwritten).
    """
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as error:
        raise StorageError(
            f"Ticket file '{path}' is not valid JSON: {error}. "
            "Fix or move the file; it was not changed."
        )

    if not isinstance(data, list) or not all(isinstance(t, dict) for t in data):
        raise StorageError(
            f"Ticket file '{path}' must contain a list of tickets."
        )
    return data


##Version 2 state:


# ---------------------------------------------------------------------------
# Version 2 state: {"schema_version": 2, "tickets": [...], "events": [...]}
# ---------------------------------------------------------------------------
from campusflow.sla import parse_iso  # noqa: E402

DEFAULT_STATE_PATH = os.path.join("data", "state.json")
SCHEMA_VERSION = 2

_STATUSES = {"open", "in_progress", "resolved"}
_PRIORITIES = {"critical", "high", "medium", "low"}
_URGENCIES = {"low", "medium", "high"}
_CATEGORIES = {"Network", "Hardware", "Software", "Other"}
_EVENT_TYPES = {"CREATE", "ASSIGN", "START", "RESOLVE", "REOPEN", "ESCALATE"}

_TICKET_FIELDS = (
    "id", "title", "category", "urgency", "affected_users", "priority",
    "status", "assigned_to", "created_at", "updated_at", "due_at",
    "escalation_cycle", "escalated_cycle",
)
_EVENT_FIELDS = (
    "event_id", "ticket_id", "event_type", "actor", "timestamp",
    "before_status", "after_status", "details",
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_text(value):
    return isinstance(value, str) and bool(value.strip())


def _check_timestamp(value, label):
    if not isinstance(value, str):
        raise StorageError(f"{label} must be an ISO-8601 string.")
    try:
        parse_iso(value)
    except ValueError:
        raise StorageError(f"{label} '{value}' is not a valid timezone-aware timestamp.")


def _check_ticket(ticket, position):
    where = f"Ticket #{position + 1}"
    if not isinstance(ticket, dict):
        raise StorageError(f"{where} must be an object.")
    missing = [name for name in _TICKET_FIELDS if name not in ticket]
    if missing:
        raise StorageError(f"{where} is missing fields: {', '.join(missing)}.")
    if not _is_text(ticket["id"]):
        raise StorageError(f"{where} has an invalid id.")
    where = f"Ticket {ticket['id']}"
    if not _is_text(ticket["title"]):
        raise StorageError(f"{where} has a blank title.")
    if ticket["category"] not in _CATEGORIES:
        raise StorageError(f"{where} has an invalid category.")
    if ticket["urgency"] not in _URGENCIES:
        raise StorageError(f"{where} has an invalid urgency.")
    if not _is_int(ticket["affected_users"]) or ticket["affected_users"] < 1:
        raise StorageError(f"{where} has invalid affected_users.")
    if ticket["priority"] not in _PRIORITIES:
        raise StorageError(f"{where} has an invalid priority.")
    if ticket["status"] not in _STATUSES:
        raise StorageError(f"{where} has an invalid status.")
    if ticket["assigned_to"] is not None and not _is_text(ticket["assigned_to"]):
        raise StorageError(f"{where} has an invalid assigned_to.")
    if ticket["status"] in ("in_progress", "resolved") and ticket["assigned_to"] is None:
        raise StorageError(f"{where} is {ticket['status']} but unassigned.")
    for name in ("created_at", "updated_at", "due_at"):
        _check_timestamp(ticket[name], f"{where} {name}")
    cycle = ticket["escalation_cycle"]
    if not _is_int(cycle) or cycle < 0:
        raise StorageError(f"{where} has an invalid escalation_cycle.")
    marker = ticket["escalated_cycle"]
    if marker is not None and (not _is_int(marker) or marker < 0 or marker > cycle):
        raise StorageError(f"{where} has an invalid escalated_cycle.")


def _check_event(event, position, ticket_ids):
    where = f"Event #{position + 1}"
    if not isinstance(event, dict):
        raise StorageError(f"{where} must be an object.")
    missing = [name for name in _EVENT_FIELDS if name not in event]
    if missing:
        raise StorageError(f"{where} is missing fields: {', '.join(missing)}.")
    if not _is_text(event["event_id"]):
        raise StorageError(f"{where} has an invalid event_id.")
    where = f"Event {event['event_id']}"
    if event["event_type"] not in _EVENT_TYPES:
        raise StorageError(f"{where} has an invalid event_type.")
    if event["ticket_id"] not in ticket_ids:
        raise StorageError(f"{where} refers to unknown ticket '{event['ticket_id']}'.")
    if not _is_text(event["actor"]):
        raise StorageError(f"{where} has a blank actor.")
    _check_timestamp(event["timestamp"], f"{where} timestamp")
    if event["before_status"] is not None and event["before_status"] not in _STATUSES:
        raise StorageError(f"{where} has an invalid before_status.")
    if event["after_status"] not in _STATUSES:
        raise StorageError(f"{where} has an invalid after_status.")
    if not isinstance(event["details"], str):
        raise StorageError(f"{where} details must be text.")


def validate_state(tickets, events):
    """Raise StorageError unless tickets and events are valid and consistent."""
    if not isinstance(tickets, list) or not isinstance(events, list):
        raise StorageError("tickets and events must both be lists.")
    ticket_ids = set()
    for position, ticket in enumerate(tickets):
        _check_ticket(ticket, position)
        if ticket["id"] in ticket_ids:
            raise StorageError(f"Duplicate ticket id '{ticket['id']}'.")
        ticket_ids.add(ticket["id"])
    event_ids = set()
    for position, event in enumerate(events):
        _check_event(event, position, ticket_ids)
        if event["event_id"] in event_ids:
            raise StorageError(f"Duplicate event id '{event['event_id']}'.")
        event_ids.add(event["event_id"])


def _atomic_write_json(data, path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=folder or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def save_state(tickets, events, path=DEFAULT_STATE_PATH):
    """Validate, then atomically write the version 2 state file."""
    validate_state(tickets, events)
    _atomic_write_json(
        {"schema_version": SCHEMA_VERSION, "tickets": tickets, "events": events},
        path,
    )


def load_state(path=DEFAULT_STATE_PATH):
    """Return (tickets, events) from a version 2 file.

    Missing file -> ([], []). Anything malformed or inconsistent raises
    StorageError and the file on disk is never modified.
    """
    if not os.path.exists(path):
        return [], []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as error:
        raise StorageError(
            f"State file '{path}' is not valid JSON: {error}. It was not changed."
        )
    if isinstance(data, list):
        raise StorageError(
            f"'{path}' is an old-format ticket list, not a version 2 file. "
            "It was not changed."
        )
    if not isinstance(data, dict):
        raise StorageError(f"'{path}' must contain a JSON object.")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise StorageError(
            f"Unsupported schema_version {data.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}."
        )
    if "tickets" not in data or "events" not in data:
        raise StorageError("State file must contain 'tickets' and 'events'.")
    validate_state(data["tickets"], data["events"])
    return data["tickets"], data["events"]
