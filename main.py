
"""CampusFlow Pro command-line helpdesk application."""

from campusflow.history import display_ticket_history
from campusflow.knowledge_lab import run_knowledge_lab
from campusflow.operations import (
    assign_with_history,
    change_status_with_history,
    create_ticket_with_history,
)
from campusflow.queue import get_ticket_queue
from campusflow.reports import (
    display_sla_attention_queue,
    display_ticket_metrics,
    format_report,
    generate_report,
)
from campusflow.sla import escalate_overdue, parse_iso
from campusflow.storage import StorageError, load_state, save_state
from campusflow.tickets import get_ticket_by_id, list_tickets


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
    print(f"Due at:         {ticket.get('due_at', 'N/A')}")
    print(f"SLA cycle:      {ticket.get('escalation_cycle', 'N/A')}")


def display_tickets(tickets):
    """Display a list of tickets in a readable format."""
    if not tickets:
        print("\nNo tickets found.")
        return
    print("\n{:<8} {:<25} {:<10} {:<12} {:<15}".format(
        "ID", "Title", "Priority", "Status", "Assigned to"))
    print("-" * 74)
    for ticket in tickets:
        print("{:<8} {:<25} {:<10} {:<12} {:<15}".format(
            ticket["id"], ticket["title"][:24], ticket["priority"],
            ticket["status"], (ticket["assigned_to"] or "Unassigned")[:14]))


def ask_operator():
    """Ask for an operator label. It is an audit label, not verified identity."""
    while True:
        label = input(
            "Operator label (used in the audit trail, not verified identity): "
        ).strip()
        if label:
            return label
        print("The operator label cannot be blank.")


def ask_as_of_time():
    """Ask for an optional UTC 'as of' time. Enter means 'now' (returns None)."""
    while True:
        text = input(
            '"As of" UTC time (e.g. 2026-10-14T12:00:00+00:00), '
            "or press Enter for now: "
        ).strip()
        if not text:
            return None
        try:
            return parse_iso(text)
        except ValueError as error:
            print(f"Invalid time: {error}")


def confirm_duplicate(matches):
    """Show likely duplicates and ask for explicit confirmation."""
    print("\nWarning: similar unresolved ticket(s) already exist:")
    for match in matches:
        print(f"  {match['id']}: {match['title']} ({match['status']})")
    return input("Create this ticket anyway? (y/n): ").strip().lower() == "y"


# Each handler returns True only when ticket or event data changed.

def create_new_ticket(tickets, events, actor):
    print("\n--- Create a Ticket ---")
    title = input("Ticket title: ")
    category = input("Category (Network/Hardware/Software/Other): ")
    urgency = input("Urgency (low/medium/high): ")
    affected_users = input("Number of affected users: ")
    try:
        ticket = create_ticket_with_history(
            tickets, events, title, category, urgency, affected_users, actor,
            confirm_duplicate=confirm_duplicate,
        )
    except ValueError as error:
        print(f"\nCould not create ticket: {error}")
        return False
    if ticket is None:
        print("Cancelled. No ticket was created.")
        return False
    print(f"\nTicket {ticket['id']} created successfully.")
    display_ticket(ticket)
    return True


def assign_existing_ticket(tickets, events, actor):
    ticket_id = input("Enter ticket ID: ")
    staff_name = input("Enter staff member's name: ")
    try:
        ticket = assign_with_history(tickets, events, ticket_id, staff_name, actor)
    except ValueError as error:
        print(f"Could not assign ticket: {error}")
        return False
    print(f"Ticket {ticket['id']} assigned to {ticket['assigned_to']}.")
    return True


def update_ticket_status(tickets, events, actor):
    ticket_id = input("Enter ticket ID: ")
    print("Available statuses: open, in_progress, resolved")
    new_status = input("Enter the new status: ")
    try:
        ticket = change_status_with_history(
            tickets, events, ticket_id, new_status, actor)
    except ValueError as error:
        print(f"Could not change status: {error}")
        return False
    print(f"Ticket {ticket['id']} status is now '{ticket['status']}'.")
    return True


def view_ticket(tickets):
    ticket = get_ticket_by_id(tickets, input("Enter ticket ID (e.g. T001): "))
    if ticket is None:
        print("Ticket not found.")
    else:
        display_ticket(ticket)
    return False


def list_and_view(tickets):
    display_tickets(list_tickets(tickets))
    return view_ticket(tickets)


def show_open_queue(tickets):
    print("\n--- Original Open Work Queue ---")
    display_tickets(get_ticket_queue(tickets))
    return False


def show_sla_queue(tickets):
    display_sla_attention_queue(tickets, ask_as_of_time())
    return False


def view_history(events):
    display_ticket_history(events, input("Enter ticket ID: ").strip())
    return False


def check_escalations(tickets, events, actor):
    now = ask_as_of_time()
    try:
        result = escalate_overdue(tickets, events, now, actor)
    except ValueError as error:
        print(f"Could not check escalations: {error}")
        return False
    print(f"\nNewly escalated:   {result['newly_escalated']}")
    print(f"Already escalated: {result['already_escalated']}")
    return result["newly_escalated"] > 0


def show_reports(tickets, events):
    now = ask_as_of_time()
    print()
    print(format_report(generate_report(tickets)))
    display_ticket_metrics(tickets, events, now)
    return False


def knowledge_lab():
    run_knowledge_lab()
    return False


def save_current(tickets, events):
    try:
        save_state(tickets, events)
    except (OSError, StorageError) as error:
        print(f"Warning: could not save: {error}")
        return False
    print("Saved.")
    return True


def save_or_load(tickets, events):
    choice = input("(S)ave now or (L)oad from file? ").strip().lower()
    if choice == "s":
        save_current(tickets, events)
    elif choice == "l":
        try:
            new_tickets, new_events = load_state()
        except StorageError as error:
            print(f"Could not load: {error}")
            print("Your current data was kept.")
            return False
        tickets[:] = new_tickets          # replace only after a successful load
        events[:] = new_events
        print(f"Loaded {len(tickets)} ticket(s) and {len(events)} event(s).")
    else:
        print("Please enter S or L.")
    return False


def display_menu():
    print("\n========== CampusFlow Pro ==========")
    print("1.  Create ticket")
    print("2.  Assign ticket")
    print("3.  Start / resolve / reopen ticket")
    print("4.  Original open queue")
    print("5.  SLA attention queue")
    print("6.  View ticket history")
    print("7.  Check and escalate overdue")
    print("8.  Reports")
    print("9.  Save / load")
    print("10. Engineering Knowledge Lab")
    print("11. List tickets / view one ticket")
    print("0.  Save and exit")
    print("====================================")


def main():
    """Start the CampusFlow application."""
    try:
        tickets, events = load_state()
    except StorageError as error:
        print(f"Could not load data safely:\n{error}")
        print("Fix or move the data file before restarting CampusFlow.")
        return

    print("Welcome to CampusFlow Pro!")
    print(f"Loaded {len(tickets)} ticket(s) and {len(events)} event(s).")
    try:
        actor = ask_operator()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting CampusFlow.")
        return

    actions = {
        "1": lambda: create_new_ticket(tickets, events, actor),
        "2": lambda: assign_existing_ticket(tickets, events, actor),
        "3": lambda: update_ticket_status(tickets, events, actor),
        "4": lambda: show_open_queue(tickets),
        "5": lambda: show_sla_queue(tickets),
        "6": lambda: view_history(events),
        "7": lambda: check_escalations(tickets, events, actor),
        "8": lambda: show_reports(tickets, events),
        "9": lambda: save_or_load(tickets, events),
        "10": knowledge_lab,
        "11": lambda: list_and_view(tickets),
    }

    while True:
        display_menu()
        try:
            choice = input("Choose an option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting CampusFlow.")
            return

        if choice == "0":
            if save_current(tickets, events) or input(
                "Exit WITHOUT saving? (y/n): "
            ).strip().lower() == "y":
                print("Thank you for using CampusFlow!")
                break
            continue

        action = actions.get(choice)
        if action is None:
            print("Invalid option. Please choose a number from 0 to 11.")
            continue

        try:
            changed = action()
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
            continue
        except (OSError, KeyError, TypeError, ValueError) as error:
            print(f"An unexpected operation error occurred: {error}")
            continue
        if changed:
            save_current(tickets, events)


if __name__ == "__main__":
    main()
