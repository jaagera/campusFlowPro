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


def create_new_ticket(tickets):
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
        save_changes(tickets)
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


def assign_existing_ticket(tickets):
    """Assign a ticket to a staff member."""
    ticket_id = input("Enter ticket ID: ")
    staff_name = input("Enter staff member's name: ")

    try:
        ticket = assign_ticket(tickets, ticket_id, staff_name)
        print(f"Ticket {ticket['id']} assigned to {ticket['assigned_to']}.")
        save_changes(tickets)
    except ValueError as error:
        print(f"Could not assign ticket: {error}")


def update_ticket_status(tickets):
    """Change a ticket's status."""
    ticket_id = input("Enter ticket ID: ")
    print("Available statuses: open, in_progress, resolved")
    new_status = input("Enter the new status: ")

    try:
        ticket = change_status(tickets, ticket_id, new_status)
        print(f"Ticket {ticket['id']} status is now '{ticket['status']}'.")
        save_changes(tickets)
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
    print("0. Save and exit")
    print("=========================================")


def main():
    """Start the CampusFlow application."""
    try:
        tickets = load_tickets()
    except StorageError as error:
        print(f"Could not load tickets safely:\n{error}")
        print("Fix the ticket file before restarting CampusFlow.")
        return

    print("Welcome to CampusFlow Helpdesk!")
    print(f"Loaded {len(tickets)} ticket(s).")

    actions = {
        "1": lambda: create_new_ticket(tickets),
        "2": lambda: display_tickets(list_tickets(tickets)),
        "3": lambda: view_ticket(tickets),
        "4": lambda: assign_existing_ticket(tickets),
        "5": lambda: update_ticket_status(tickets),
        "6": lambda: show_priority_queue(tickets),
        "7": lambda: show_reports(tickets),
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
            print("Thank you for using CampusFlow!")
            break

        action = actions.get(choice)

        if action is None:
            print("Invalid option. Please choose a number from 0 to 7.")
            continue

        try:
            action()
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
        except (OSError, KeyError, TypeError, ValueError) as error:
            print(f"An unexpected operation error occurred: {error}")


if __name__ == "__main__":
    main()