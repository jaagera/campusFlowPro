
from campusflow.storage import load_tickets, save_tickets, StorageError
from campusflow.event_storage import load_events, save_events
from campusflow.history import record_event, display_ticket_history
##NEW

from campusflow.history import display_ticket_history

from campusflow.reports import (
    detect_duplicates,
    display_sla_attention_queue,
    display_ticket_metrics,
)

from campusflow.knowledge_lab import run_knowledge_lab




"""CampusFlow command-line helpdesk application."""

from campusflow.tickets import (
    create_ticket,
    list_tickets,
    get_ticket_by_id,
)
from campusflow.workflow import assign_ticket, change_status
from campusflow.queue import get_ticket_queue
from campusflow.reports import generate_report, format_report
from campusflow.storage import load_tickets, save_tickets, StorageError


def display_ticket(ticket):
    """Display the details of one ticket."""
    print("\n--- Ticket Details ---")
    print(f"ID:             {ticket['id']}")
    print(f"Title:          {ticket['title']}")
    print(f"Category:       {ticket['category']}")
    print(f"Urgency:        {ticket['urgency']}")
    print(f"Affected users: {ticket['affected_users']}")
    print(f"Priority:       {ticket['priority']}")
    print(f"Status:         {ticket['status']}")
    print(f"Assigned to:    {ticket['assigned_to'] or 'Unassigned'}")


def display_tickets(tickets):
    """Display a list of tickets in a readable format."""
    if not tickets:
        print("\nNo tickets found.")
        return

    print("\n{:<8} {:<25} {:<12} {:<12} {:<15}".format(
        "ID", "Title", "Priority", "Status", "Assigned to"
    ))
    print("-" * 76)

    for ticket in tickets:
        title = ticket["title"][:24]
        assigned = ticket["assigned_to"] or "Unassigned"
        print("{:<8} {:<25} {:<12} {:<12} {:<15}".format(
            ticket["id"],
            title,
            ticket["priority"],
            ticket["status"],
            assigned[:14],
        ))


def save_changes(tickets):
    """Save ticket changes and report any saving errors."""
    try:
        save_tickets(tickets)
        print("Changes saved successfully.")
    except (OSError, StorageError, TypeError, ValueError) as error:
        print(f"Warning: Could not save changes: {error}")
        print("The changes may still exist in memory, but are not saved.")


def save_event_changes(events):
    """Save audit events and report any saving errors."""
    try:
        save_events(events)
    except (OSError, StorageError, TypeError, ValueError) as error:
        print(f"Warning: Could not save audit events: {error}")


def create_new_ticket(tickets, events):
    """Collect user input and create a ticket."""
    print("\n--- Create a Ticket ---")

    title = input("Ticket title: ")
    category = input("Category (Network/Hardware/Software/Other): ")
    urgency = input("Urgency (low/medium/high): ")
    affected_users = input("Number of affected users: ")

    try:
        ticket = create_ticket(
            tickets,
            title,
            category,
            urgency,
            affected_users,
        )

        print(f"\nTicket {ticket['id']} created successfully.")
        display_ticket(ticket)

        record_event(
            events,
            ticket["id"],
            "CREATE",
            actor="user",
            after_status=ticket["status"],
            details=f"Created ticket: {ticket['title']}",
        )

        save_changes(tickets)
        save_event_changes(events)

    except ValueError as error:
        print(f"\nCould not create ticket: {error}")


def view_ticket(tickets):
    """Find and display a ticket by ID."""
    ticket_id = input("Enter ticket ID (e.g. T001): ")
    ticket = get_ticket_by_id(tickets, ticket_id)

    if ticket is None:
        print("Ticket not found.")
    else:
        display_ticket(ticket)

ticket_before = get_ticket_by_id(tickets, ticket_id)

ticket = assign_ticket(tickets, ticket_id, staff_name)


def assign_existing_ticket(tickets, events):
    """Assign a ticket to a staff member and record the audit event."""
    ticket_id = input("Enter ticket ID: ")
    staff_name = input("Enter staff member's name: ")

    try:
        ticket_before = get_ticket_by_id(tickets, ticket_id)

        if ticket_before is None:
            print("Could not assign ticket: Ticket not found.")
            return

        before_status = ticket_before["status"]
        before_assignee = ticket_before.get("assigned_to")

        ticket = assign_ticket(tickets, ticket_id, staff_name)

        print(f"Ticket {ticket['id']} assigned to {ticket['assigned_to']}.")

        record_event(
            events,
            ticket["id"],
            "ASSIGN",
            actor="user",
            before_status=before_status,
            after_status=ticket["status"],
            details=(
                f"Previous assignee: {before_assignee or 'Unassigned'}; "
                f"New assignee: {ticket['assigned_to']}"
            ),
        )

        save_changes(tickets)
        save_event_changes(events)

    except ValueError as error:
        print(f"Could not assign ticket: {error}")




def update_ticket_status(tickets, events):
    """Change a ticket's status and record the audit event."""
    ticket_id = input("Enter ticket ID: ")
    print("Available statuses: open, in_progress, resolved")
    new_status = input("Enter the new status: ")

    try:
        ticket_before = get_ticket_by_id(tickets, ticket_id)

        if ticket_before is None:
            print("Could not change status: Ticket not found.")
            return

        before_status = ticket_before["status"]

        ticket = change_status(tickets, ticket_id, new_status)

        print(f"Ticket {ticket['id']} status is now '{ticket['status']}'.")

        record_event(
            events,
            ticket["id"],
                        {
                "open": "REOPEN",
                "in_progress": "START",
                "resolved": "RESOLVE",
            }.get(ticket["status"], "START"),
            actor="user",
            before_status=before_status,
            after_status=ticket["status"],
            details=f"Status changed from {before_status} to {ticket['status']}",
        )

        save_changes(tickets)
        save_event_changes(events)

    except ValueError as error:
        print(f"Could not change status: {error}")



def show_priority_queue(tickets):
    """Display open tickets in priority order."""
    queue = get_ticket_queue(tickets)
    print("\n--- Open Ticket Priority Queue ---")
    display_tickets(queue)


def show_reports(tickets):
    """Display a ticket summary report."""
    report = generate_report(tickets)
    print()
    print(format_report(report))


def view_ticket_history(events):
    """Display the audit history for a ticket."""
    ticket_id = input("Enter ticket ID: ").strip()
    display_ticket_history(events, ticket_id)


def display_menu():
    """Display the main menu."""
    print("\n========== CampusFlow Helpdesk ==========")
    print("1. Create ticket")
    print("2. List all tickets")
    print("3. View ticket details")
    print("4. Assign ticket")
    print("5. Change ticket status")
    print("6. View priority queue")
    print("7. View reports")
    print("8. View ticket history")
    print("0. Save and exit")
    print("=========================================")


def main():
    """Start the CampusFlow application."""
   
    try:
        tickets = load_tickets()
        events = load_events()
    except StorageError as error:
        print(f"Could not load data safely:\n{error}")
        print("Fix the affected data file before restarting CampusFlow.")
        return

    print("Welcome to CampusFlow Helpdesk!")
    print(f"Loaded {len(tickets)} ticket(s).")

    actions = {
        "1": lambda: create_new_ticket(tickets, events),
        "2": lambda: display_tickets(list_tickets(tickets)),
        "3": lambda: view_ticket(tickets),
        "4": lambda: assign_existing_ticket(tickets, events),
        "5": lambda: update_ticket_status(tickets, events),
        "6": lambda: show_priority_queue(tickets),
        "7": lambda: show_reports(tickets),
        "8": lambda: view_ticket_history(events),
    }

    while True:
        display_menu()

        try:
            choice = input("Choose an option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting CampusFlow.")
            return

        if choice == "0":
            save_changes(tickets)
            save_event_changes(events)
            print("Thank you for using CampusFlow!")
            break

        action = actions.get(choice)

        if action is None:
            print("Invalid option. Please choose a number from 0 to 8.")
            continue

        try:
            action()
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
        except (OSError, KeyError, TypeError, ValueError) as error:
            print(f"An unexpected operation error occurred: {error}")


if __name__ == "__main__":
    main()