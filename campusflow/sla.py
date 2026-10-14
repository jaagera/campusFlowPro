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

##ADDED

def init_ticket_sla(ticket, now=None):
    """Add the SLA fields to a brand-new ticket (cycle starts at creation)."""
    if now is None:
        now = utc_now()
    stamp = to_iso(now)
    ticket["created_at"] = stamp
    ticket["updated_at"] = stamp
    ticket["escalation_cycle"] = 0
    ticket["escalated_cycle"] = None
    start_sla_cycle(ticket, now)
    return ticket


def restart_sla_cycle(ticket, now=None):
    """Start a NEW SLA cycle on reopen. created_at is left untouched."""
    if now is None:
        now = utc_now()
    ticket["escalation_cycle"] += 1
    ticket["updated_at"] = to_iso(now)
    start_sla_cycle(ticket, now)
    return ticket


def is_escalated_this_cycle(ticket):
    """True if this ticket already escalated in its current SLA cycle."""
    return ticket.get("escalated_cycle") == ticket["escalation_cycle"]


def _next_event_id(events):
    highest = 0
    for event in events:
        try:
            highest = max(highest, int(str(event["event_id"]).lstrip("E")))
        except (KeyError, ValueError):
            continue
    return f"E{highest + 1:03d}"


def escalate_overdue(tickets, events, now=None, actor="operator"):
    """Create exactly one ESCALATE event per overdue ticket per SLA cycle.

    Does not assign the ticket or change its priority or status.
    Returns {"newly_escalated": n, "already_escalated": m, "events": [...]}.
    """
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("Actor label must not be blank.")
    actor = actor.strip()
    if now is None:
        now = utc_now()

    newly = 0
    already = 0
    new_events = []
    for ticket in tickets:
        if not is_overdue(ticket, now):
            continue
        if is_escalated_this_cycle(ticket):
            already += 1
            continue
        event = {
            "event_id": _next_event_id(events),
            "ticket_id": ticket["id"],
            "event_type": "ESCALATE",
            "actor": actor,
            "timestamp": to_iso(now),
            "before_status": ticket["status"],
            "after_status": ticket["status"],
            "details": f"SLA cycle {ticket['escalation_cycle']} overdue "
                       f"(due {ticket['due_at']})",
        }
        events.append(event)
        ticket["escalated_cycle"] = ticket["escalation_cycle"]
        ticket["updated_at"] = to_iso(now)
        new_events.append(event)
        newly += 1

    return {
        "newly_escalated": newly,
        "already_escalated": already,
        "events": new_events,
    }
