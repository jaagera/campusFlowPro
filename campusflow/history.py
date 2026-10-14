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
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def record_event(
    events,
    ticket_id,
    event_type,
    actor,
    before_status,
    after_status,
    details="",
    timestamp=None,
):
    """Append an event after a ticket operation succeeds."""

    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event type: {event_type}")

    if not ticket_id:
        raise ValueError("Ticket ID is required.")

    if not actor or not actor.strip():
        raise ValueError("Actor label is required.")

    event_time = timestamp or utc_now()

    event = {
        "event_id": f"E{len(events) + 1:04d}",
        "ticket_id": ticket_id,
        "event_type": event_type,
        "actor": actor.strip(),
        "timestamp": event_time.isoformat(),
        "before_status": before_status,
        "after_status": after_status,
        "details": details,
    }

    events.append(event)

    return event


def get_ticket_history(events, ticket_id):
    """Return a ticket's events in chronological order."""

    matching_events = [
        event
        for event in events
        if event["ticket_id"] == ticket_id
    ]

    return sorted(
        matching_events,
        key=lambda event: (
            event["timestamp"],
            event["event_id"],
        ),
    )


def display_ticket_history(events, ticket_id):
    """Print the audit history for one ticket."""

    history = get_ticket_history(events, ticket_id)

    if not history:
        print(f"No history found for ticket {ticket_id}.")
        return

    print(f"\n===== HISTORY: {ticket_id} =====")

    for event in history:
        print(f"Event ID: {event['event_id']}")
        print(f"Action: {event['event_type']}")
        print(f"Actor: {event['actor']}")
        print(f"Time: {event['timestamp']}")
        print(
            f"Status: {event['before_status']} "
            f"-> {event['after_status']}"
        )
        print(f"Details: {event['details']}")
        print("-" * 35)


##NEW

"""Audit history for successful CampusFlow ticket operations."""

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
    """Return the current UTC timestamp."""
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

    event = {
        "event_id": f"E{len(events) + 1:04d}",
        "ticket_id": str(ticket_id).strip().upper(),
        "event_type": event_type,
        "actor": actor,
        "timestamp": timestamp or utc_now(),
        "before_status": before_status,
        "after_status": after_status,
        "details": details,
    }

    events.append(event)
    return event


def get_ticket_history(events, ticket_id):
    """Return all events for one ticket, in chronological order."""
    normalized_id = str(ticket_id).strip().upper()

    matching_events = [
        event
        for event in events
        if event["ticket_id"] == normalized_id
    ]

    return sorted(
        matching_events,
        key=lambda event: (event["timestamp"], event["event_id"]),
    )


def display_ticket_history(events, ticket_id):
    """Print the audit history for one ticket."""
    history = get_ticket_history(events, ticket_id)

    if not history:
        print(f"No history found for ticket {ticket_id}.")
        return

    print(f"\n--- History for Ticket {str(ticket_id).strip().upper()} ---")

    for event in history:
        print(f"Event ID:      {event['event_id']}")
        print(f"Type:          {event['event_type']}")
        print(f"Actor:         {event['actor']}")
        print(f"Timestamp:     {event['timestamp']}")
        print(f"Before status: {event['before_status'] or 'N/A'}")
        print(f"After status:  {event['after_status'] or 'N/A'}")

        if event["details"]:
            print(f"Details:       {event['details']}")

        print("-" * 40)
