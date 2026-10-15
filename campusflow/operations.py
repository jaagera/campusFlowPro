"""Ticket operations that record audit events only after they succeed."""

import copy

from campusflow.duplicates import detect_duplicates
from campusflow.history import record_event
from campusflow.sla import init_ticket_sla, restart_sla_cycle, to_iso, utc_now
from campusflow.tickets import create_ticket, get_ticket_by_id
from campusflow.workflow import assign_ticket, change_status


def _require_actor(actor):
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("Actor label must not be blank.")
    return actor.strip()


def _restore(ticket, snapshot):
    ticket.clear()
    ticket.update(snapshot)


def create_ticket_with_history(
    tickets, events, title, category, urgency, affected_users, actor,
    now=None, confirm_duplicate=None,
):
    """Create a ticket, start its SLA cycle and record a CREATE event.

    If an unresolved duplicate exists, confirm_duplicate(matches) must return
    True to continue. Declining (or passing no callback) creates neither a
    ticket nor an event and returns None.
    """
    actor = _require_actor(actor)
    now = now or utc_now()

    matches = detect_duplicates(tickets, category, title)
    if matches:
        if confirm_duplicate is None or not confirm_duplicate(matches):
            return None

    ticket_count = len(tickets)
    ticket = create_ticket(tickets, title, category, urgency, affected_users)
    try:
        init_ticket_sla(ticket, now)
        record_event(
            events, ticket["id"], "CREATE", actor, None, ticket["status"],
            details=f"created: {ticket['title']}", timestamp=now,
        )
    except Exception:
        del tickets[ticket_count:]
        raise
    return ticket


def assign_with_history(tickets, events, ticket_id, staff_name, actor, now=None):
    """Assign a ticket and record an ASSIGN event."""
    actor = _require_actor(actor)
    now = now or utc_now()

    found = get_ticket_by_id(tickets, ticket_id)
    snapshot = copy.deepcopy(found) if found is not None else None

    ticket = assign_ticket(tickets, ticket_id, staff_name)  # raises if invalid
    try:
        ticket["updated_at"] = to_iso(now)
        record_event(
            events, ticket["id"], "ASSIGN", actor,
            ticket["status"], ticket["status"],
            details=f"assigned to {ticket['assigned_to']}", timestamp=now,
        )
    except Exception:
        if snapshot is not None:
            _restore(ticket, snapshot)
        raise
    return ticket


def _event_type_for(before, after):
    if after == "in_progress":
        return "START"
    if after == "resolved":
        return "RESOLVE"
    if before == "resolved" and after == "open":
        return "REOPEN"
    raise ValueError(f"No event type for {before} -> {after}.")


def change_status_with_history(tickets, events, ticket_id, new_status, actor, now=None):
    """Change status, update SLA fields and record START, RESOLVE or REOPEN."""
    actor = _require_actor(actor)
    now = now or utc_now()

    found = get_ticket_by_id(tickets, ticket_id)
    snapshot = copy.deepcopy(found) if found is not None else None
    before = found["status"] if found is not None else None

    ticket = change_status(tickets, ticket_id, new_status)  # raises if invalid
    try:
        if before == "resolved" and ticket["status"] == "open":
            restart_sla_cycle(ticket, now)      # new cycle, created_at kept
        else:
            ticket["updated_at"] = to_iso(now)
        record_event(
            events, ticket["id"], _event_type_for(before, ticket["status"]),
            actor, before, ticket["status"],
            details=f"status {before} -> {ticket['status']}", timestamp=now,
        )
    except Exception:
        if snapshot is not None:
            _restore(ticket, snapshot)
        raise
    return ticket
