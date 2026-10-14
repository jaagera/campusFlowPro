
STATUSES = ("open", "in_progress", "resolved")
PRIORITIES = ("critical", "high", "medium", "low")


def generate_report(tickets):
    """Return a summary of the tickets as a dictionary.

    {
        "total": int,
        "by_status": {"open": n, "in_progress": n, "resolved": n},
        "by_priority": {"critical": n, "high": n, "medium": n, "low": n},
    }

    Every known status and priority is always present, with 0 when
    there are no matching tickets, so an empty list still works.
    """
    by_status = {status: 0 for status in STATUSES}
    by_priority = {priority: 0 for priority in PRIORITIES}

    for ticket in tickets:
        status = ticket["status"]
        priority = ticket["priority"]
        by_status[status] = by_status.get(status, 0) + 1
        by_priority[priority] = by_priority.get(priority, 0) + 1

    return {
        "total": len(tickets),
        "by_status": by_status,
        "by_priority": by_priority,
    }


def format_report(report):
    """Turn a report dictionary into text the CLI can print."""
    lines = ["=== CampusFlow Report ===", f"Total tickets: {report['total']}", ""]
    lines.append("By status:")
    for status, count in report["by_status"].items():
        lines.append(f"  {status}: {count}")
    lines.append("")
    lines.append("By priority:")
    for priority, count in report["by_priority"].items():
        lines.append(f"  {priority}: {count}")
    return "\n".join(lines)

##NEW

"""Duplicate detection, SLA queues and ticket reports."""

from datetime import datetime, timezone


def normalize_title(title):
    """Normalize a title for duplicate comparison."""
    return " ".join(title.casefold().split())


def detect_duplicates(category, title, tickets):
    """
    Find unresolved tickets with the same normalized title
    and category.
    """

    normalized_title = normalize_title(title)
    normalized_category = category.casefold().strip()

    duplicates = []

    for ticket in tickets:
        if ticket.get("status") == "resolved":
            continue

        existing_title = normalize_title(ticket.get("title", ""))
        existing_category = ticket.get("category", "").casefold().strip()

        if (
            existing_title == normalized_title
            and existing_category == normalized_category
        ):
            duplicates.append(ticket)

    return duplicates


def parse_utc(timestamp):
    """Parse an ISO timestamp and ensure it is timezone-aware."""

    parsed = datetime.fromisoformat(timestamp)

    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")

    return parsed.astimezone(timezone.utc)


def is_ticket_overdue(ticket, now):
    """Check whether an unresolved ticket is overdue."""

    if ticket.get("status") == "resolved":
        return False

    due_at = parse_utc(ticket["due_at"])

    if now.tzinfo is None:
        raise ValueError("'now' must include a timezone.")

    current_time = now.astimezone(timezone.utc)

    return current_time > due_at


def sla_attention_queue(tickets, now=None):
    """
    Return unresolved tickets ordered by:
    1. Overdue tickets first.
    2. Earliest due date.
    3. Ticket ID.
    """

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("'now' must include a timezone.")

    unresolved = [
        ticket
        for ticket in tickets
        if ticket.get("status") in {"open", "in_progress"}
    ]

    return sorted(
        unresolved,
        key=lambda ticket: (
            not is_ticket_overdue(ticket, now),
            parse_utc(ticket["due_at"]),
            ticket["id"],
        ),
    )


def ticket_metrics(tickets, events, now=None):
    """Calculate read-only ticket metrics."""

    if now is None:
        now = datetime.now(timezone.utc)

    metrics = {
        "open_count": 0,
        "in_progress_count": 0,
        "resolved_count": 0,
        "overdue_unresolved_count": 0,
        "escalated_in_current_cycle_count": 0,
        "priority_counts": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        },
    }

    for ticket in tickets:
        status = ticket.get("status")

        if status == "open":
            metrics["open_count"] += 1
        elif status == "in_progress":
            metrics["in_progress_count"] += 1
        elif status == "resolved":
            metrics["resolved_count"] += 1

        priority = ticket.get("priority")

        if priority in metrics["priority_counts"]:
            metrics["priority_counts"][priority] += 1

        if (
            status in {"open", "in_progress"}
            and is_ticket_overdue(ticket, now)
        ):
            metrics["overdue_unresolved_count"] += 1

    for ticket in tickets:
        current_cycle = ticket.get("escalation_cycle", 0)

        has_current_escalation = any(
            event.get("ticket_id") == ticket["id"]
            and event.get("event_type") == "ESCALATE"
            and event.get("escalation_cycle") == current_cycle
            for event in events
        )

        if has_current_escalation:
            metrics["escalated_in_current_cycle_count"] += 1

    return metrics


def display_sla_attention_queue(tickets, now=None):
    """Display the SLA Attention Queue."""

    queue = sla_attention_queue(tickets, now)

    if not queue:
        print("No unresolved tickets.")
        return

    print("\n===== SLA ATTENTION QUEUE =====")

    if now is None:
        now = datetime.now(timezone.utc)

    for ticket in queue:
        overdue = is_ticket_overdue(ticket, now)

        label = "OVERDUE" if overdue else "NOT OVERDUE"

        print(
            f"{ticket['id']} | "
            f"{ticket['title']} | "
            f"{ticket['priority']} | "
            f"{ticket['status']} | "
            f"Due: {ticket['due_at']} | "
            f"{label}"
        )


def display_ticket_metrics(tickets, events, now=None):
    """Display ticket counts and priority metrics."""

    metrics = ticket_metrics(tickets, events, now)

    print("\n===== CAMPUSFLOW REPORT =====")

    print(f"Open: {metrics['open_count']}")
    print(f"In progress: {metrics['in_progress_count']}")
    print(f"Resolved: {metrics['resolved_count']}")
    print(
        "Overdue unresolved: "
        f"{metrics['overdue_unresolved_count']}"
    )
    print(
        "Escalated in current cycle: "
        f"{metrics['escalated_in_current_cycle_count']}"
    )

    print("\nTickets by priority:")

    for priority, count in metrics["priority_counts"].items():
        print(f"{priority.title()}: {count}")