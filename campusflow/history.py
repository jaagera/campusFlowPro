
"""Audit history for CampusFlow ticket operations."""

from datetime import datetime, timezone


EVENT_TYPES = {
    "CREATE",
    "ASSIGN",
    "START",
    "RESOLVE",
    "REOPEN",
    "ESCALATE",
}


def utc_now():
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def record_event(
    events,
    ticket_id,
    event_type,
    actor="system",
    before_status=None,
    after_status=None,
    details="",
    timestamp=None,
):
    """Record a successful ticket operation."""

    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event type: {event_type}")

    normalized_id = str(ticket_id).strip().upper()

    if not normalized_id:
        raise ValueError("Ticket ID is required.")

    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("Actor label is required.")

    event_time = timestamp or utc_now()

    if isinstance(event_time, datetime):
        event_time = event_time.isoformat()

    event = {
        "event_id": f"E{len(events) + 1:04d}",
        "ticket_id": normalized_id,
        "event_type": event_type,
        "actor": actor.strip(),
        "timestamp": event_time,
        "before_status": before_status,
        "after_status": after_status,
        "details": details,
    }

    events.append(event)
    return event


def get_ticket_history(events, ticket_id):
    """Return one ticket's events in chronological order."""

    normalized_id = str(ticket_id).strip().upper()

    matching_events = [
        event
        for event in events
        if str(event.get("ticket_id", "")).strip().upper()
        == normalized_id
    ]

    return sorted(
        matching_events,
        key=lambda event: (
            event.get("timestamp", ""),
            event.get("event_id", ""),
        ),
    )


def display_ticket_history(events, ticket_id):
    """Display the audit history for one ticket."""

    normalized_id = str(ticket_id).strip().upper()
    history = get_ticket_history(events, normalized_id)

    if not history:
        print(f"No history found for ticket {normalized_id}.")
        return

    print(f"\n--- History for Ticket {normalized_id} ---")

    for event in history:
        print(f"Event ID:      {event.get('event_id', 'N/A')}")
        print(f"Type:          {event.get('event_type', 'N/A')}")
        print(f"Actor:         {event.get('actor', 'N/A')}")
        print(f"Timestamp:     {event.get('timestamp', 'N/A')}")
        print(
            f"Before status: "
            f"{event.get('before_status') or 'N/A'}"
        )
        print(
            f"After status:  "
            f"{event.get('after_status') or 'N/A'}"
        )

        details = event.get("details", "")
        if details:
            print(f"Details:       {details}")

        print("-" * 40)
