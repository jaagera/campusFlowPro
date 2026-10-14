from datetime import datetime, timedelta, timezone

SLA_MINUTES = {
    "critical": 60,
    "high": 240,
    "medium": 1440,
    "low": 2880,
}


def utc_now():
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso(moment):
    """Serialize an aware datetime as an ISO-8601 UTC string."""
    if moment.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware.")
    return moment.astimezone(timezone.utc).isoformat()


def parse_iso(text):
    """Parse an ISO-8601 string into an aware UTC datetime."""
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError(f"Timestamp '{text}' has no timezone.")
    return moment.astimezone(timezone.utc)


def calculate_due_at(priority, cycle_start):
    """Return cycle_start plus the SLA duration for this priority."""
    if priority not in SLA_MINUTES:
        raise ValueError(f"Unknown priority '{priority}'.")
    if cycle_start.tzinfo is None:
        raise ValueError("cycle_start must be timezone-aware.")
    return cycle_start + timedelta(minutes=SLA_MINUTES[priority])


def start_sla_cycle(ticket, cycle_start):
    """Set a ticket's due_at from a cycle start time."""
    due = calculate_due_at(ticket["priority"], cycle_start)
    ticket["due_at"] = to_iso(due)
    return ticket


def is_overdue(ticket, now=None):
    """True only if now is STRICTLY later than due_at and the ticket is unresolved."""
    if ticket["status"] == "resolved":
        return False
    if now is None:
        now = utc_now()
    return now > parse_iso(ticket["due_at"])
