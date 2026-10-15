[1mdiff --git a/main.py b/main.py[m
[1mindex b4f8b0b..1b3f808 100644[m
[1m--- a/main.py[m
[1m+++ b/main.py[m
[36m@@ -1,176 +1,8 @@[m
 [m
[31m-from campusflow.storage import load_tickets, save_tickets, StorageError[m
[31m-from campusflow.event_storage import load_events, save_events[m
[31m-from campusflow.history import record_event, display_ticket_history[m
[31m-##NEW[m
[31m-[m
[31m-from campusflow.history import display_ticket_history[m
[31m-[m
[31m-from campusflow.reports import ([m
[31m-    detect_duplicates,[m
[31m-    display_sla_attention_queue,[m
[31m-    display_ticket_metrics,[m
[31m-)[m
[31m-[m
[31m-from campusflow.knowledge_lab import run_knowledge_lab[m
[31m-[m
[31m-[m
[31m-[m
[31m-[m
[31m-"""CampusFlow command-line helpdesk application."""[m
[31m-[m
[31m-from campusflow.tickets import ([m
[31m-    create_ticket,[m
[31m-    list_tickets,[m
[31m-    get_ticket_by_id,[m
[31m-)[m
[31m-from campusflow.workflow import assign_ticket, change_status[m
[31m-from campusflow.queue import get_ticket_queue[m
[31m-from campusflow.reports import generate_report, format_report[m
[31m-from campusflow.storage import load_tickets, save_tickets, StorageError[m
[31m-[m
[31m-[m
[31m-def display_ticket(ticket):[m
[31m-    """Display the details of one ticket."""[m
[31m-    print("\n--- Ticket Details ---")[m
[31m-    print(f"ID:             {ticket['id']}")[m
[31m-    print(f"Title:          {ticket['title']}")[m
[31m-    print(f"Category:       {ticket['category']}")[m
[31m-    print(f"Urgency:        {ticket['urgency']}")[m
[31m-    print(f"Affected users: {ticket['affected_users']}")[m
[31m-    print(f"Priority:       {ticket['priority']}")[m
[31m-    print(f"Status:         {ticket['status']}")[m
[31m-    print(f"Assigned to:    {ticket['assigned_to'] or 'Unassigned'}")[m
[31m-[m
[31m-[m
[31m-def display_tickets(tickets):[m
[31m-    """Display a list of tickets in a readable format."""[m
[31m-    if not tickets:[m
[31m-        print("\nNo tickets found.")[m
[31m-        return[m
[31m-[m
[31m-    print("\n{:<8} {:<25} {:<12} {:<12} {:<15}".format([m
[31m-        "ID", "Title", "Priority", "Status", "Assigned to"[m
[31m-    ))[m
[31m-    print("-" * 76)[m
[31m-[m
[31m-    for ticket in tickets:[m
[31m-        title = ticket["title"][:24][m
[31m-        assigned = ticket["assigned_to"] or "Unassigned"[m
[31m-        print("{:<8} {:<25} {:<12} {:<12} {:<15}".format([m
[31m-            ticket["id"],[m
[31m-            title,[m
[31m-            ticket["priority"],[m
[31m-            ticket["status"],[m
[31m-            assigned[:14],[m
[31m-        ))[m
[31m-[m
[31m-[m
[31m-def save_changes(tickets):[m
[31m-    """Save ticket changes and report any saving errors."""[m
[31m-    try:[m
[31m-        save_tickets(tickets)[m
[31m-        print("Changes saved successfully.")[m
[31m-    except (OSError, StorageError, TypeError, ValueError) as error:[m
[31m-        print(f"Warning: Could not save changes: {error}")[m
[31m-        print("The changes may still exist in memory, but are not saved.")[m
[31m-[m
[31m-[m
[31m-def save_event_changes(events):[m
[31m-    """Save audit events and report any saving errors."""[m
[31m-    try:[m
[31m-        save_events(events)[m
[31m-    except (OSError, StorageError, TypeError, ValueError) as error:[m
[31m-        print(f"Warning: Could not save audit events: {error}")[m
[31m-[m
[31m-[m
[31m-def create_new_ticket(tickets, events):[m
[31m-    """Collect user input and create a ticket."""[m
[31m-    print("\n--- Create a Ticket ---")[m
[31m-[m
[31m-    title = input("Ticket title: ")[m
[31m-    category = input("Category (Network/Hardware/Software/Other): ")[m
[31m-    urgency = input("Urgency (low/medium/high): ")[m
[31m-    affected_users = input("Number of affected users: ")[m
[31m-[m
[31m-    try:[m
[31m-        ticket = create_ticket([m
[31m-            tickets,[m
[31m-            title,[m
[31m-            category,[m
[31m-            urgency,[m
[31m-            affected_users,[m
[31m-        )[m
[31m-[m
[31m-        print(f"\nTicket {ticket['id']} created successfully.")[m
[31m-        display_ticket(ticket)[m
[31m-[m
[31m-        record_event([m
[31m-            events,[m
[31m-            ticket["id"],[m
[31m-            "CREATE",[m
[31m-            actor="user",[m
[31m-            after_status=ticket["status"],[m
[31m-            details=f"Created ticket: {ticket['title']}",[m
[31m-        )[m
[31m-[m
[31m-        save_changes(tickets)[m
[31m-        save_event_changes(events)[m
[31m-[m
[31m-    except ValueError as error:[m
[31m-        print(f"\nCould not create ticket: {error}")[m
[31m-[m
[31m-[m
[31m-def view_ticket(tickets):[m
[31m-    """Find and display a ticket by ID."""[m
[32m+[m[32mdef view_ticket_history(events):[m
[32m+[m[32m    """Ask for a ticket ID and display its audit history."""[m
     ticket_id = input("Enter ticket ID (e.g. T001): ")[m
[31m-    ticket = get_ticket_by_id(tickets, ticket_id)[m
[31m-[m
[31m-    if ticket is None:[m
[31m-        print("Ticket not found.")[m
[31m-    else:[m
[31m-        display_ticket(ticket)[m
[31m-[m
[31m-[m
[31m-def assign_existing_ticket(tickets):[m
[31m-    """Assign a ticket to a staff member."""[m
[31m-    ticket_id = input("Enter ticket ID: ")[m
[31m-    staff_name = input("Enter staff member's name: ")[m
[31m-[m
[31m-    try:[m
[31m-        ticket = assign_ticket(tickets, ticket_id, staff_name)[m
[31m-        print(f"Ticket {ticket['id']} assigned to {ticket['assigned_to']}.")[m
[31m-        save_changes(tickets)[m
[31m-    except ValueError as error:[m
[31m-        print(f"Could not assign ticket: {error}")[m
[31m-[m
[31m-[m
[31m-def update_ticket_status(tickets):[m
[31m-    """Change a ticket's status."""[m
[31m-    ticket_id = input("Enter ticket ID: ")[m
[31m-    print("Available statuses: open, in_progress, resolved")[m
[31m-    new_status = input("Enter the new status: ")[m
[31m-[m
[31m-    try:[m
[31m-        ticket = change_status(tickets, ticket_id, new_status)[m
[31m-        print(f"Ticket {ticket['id']} status is now '{ticket['status']}'.")[m
[31m-        save_changes(tickets)[m
[31m-    except ValueError as error:[m
[31m-        print(f"Could not change status: {error}")[m
[31m-[m
[31m-[m
[31m-def show_priority_queue(tickets):[m
[31m-    """Display open tickets in priority order."""[m
[31m-    queue = get_ticket_queue(tickets)[m
[31m-    print("\n--- Open Ticket Priority Queue ---")[m
[31m-    display_tickets(queue)[m
[31m-[m
[31m-[m
[31m-def show_reports(tickets):[m
[31m-    """Display a ticket summary report."""[m
[31m-    report = generate_report(tickets)[m
[31m-    print()[m
[31m-    print(format_report(report))[m
[32m+[m[32m    display_ticket_history(events, ticket_id)[m
 [m
 [m
 def display_menu():[m
[36m@@ -183,6 +15,7 @@[m [mdef display_menu():[m
     print("5. Change ticket status")[m
     print("6. View priority queue")[m
     print("7. View reports")[m
[32m+[m[32m    print("8. View ticket history")[m
     print("0. Save and exit")[m
     print("=========================================")[m
 [m
[36m@@ -191,22 +24,25 @@[m [mdef main():[m
     """Start the CampusFlow application."""[m
     try:[m
         tickets = load_tickets()[m
[32m+[m[32m        events = load_events()[m
     except StorageError as error:[m
[31m-        print(f"Could not load tickets safely:\n{error}")[m
[31m-        print("Fix the ticket file before restarting CampusFlow.")[m
[32m+[m[32m        print(f"Could not load data safely:\n{error}")[m
[32m+[m[32m        print("Fix the affected data file before restarting CampusFlow.")[m
         return[m
 [m
     print("Welcome to CampusFlow Helpdesk!")[m
     print(f"Loaded {len(tickets)} ticket(s).")[m
[32m+[m[32m    print(f"Loaded {len(events)} audit event(s).")[m
 [m
     actions = {[m
[31m-        "1": lambda: create_new_ticket(tickets),[m
[32m+[m[32m        "1": lambda: create_new_ticket(tickets, events),[m
         "2": lambda: display_tickets(list_tickets(tickets)),[m
         "3": lambda: view_ticket(tickets),[m
[31m-        "4": lambda: assign_existing_ticket(tickets),[m
[31m-        "5": lambda: update_ticket_status(tickets),[m
[32m+[m[32m        "4": lambda: assign_existing_ticket(tickets, events),[m
[32m+[m[32m        "5": lambda: update_ticket_status(tickets, events),[m
         "6": lambda: show_priority_queue(tickets),[m
         "7": lambda: show_reports(tickets),[m
[32m+[m[32m        "8": lambda: view_ticket_history(events),[m
     }[m
 [m
     while True:[m
[36m@@ -216,17 +52,18 @@[m [mdef main():[m
             choice = input("Choose an option: ").strip()[m
         except (EOFError, KeyboardInterrupt):[m
             print("\nExiting CampusFlow.")[m
[31m-            return[m
[32m+[m[32m            break[m
 [m
         if choice == "0":[m
             save_changes(tickets)[m
[32m+[m[32m            save_event_changes(events)[m
             print("Thank you for using CampusFlow!")[m
             break[m
 [m
         action = actions.get(choice)[m
 [m
         if action is None:[m
[31m-            print("Invalid option. Please choose a number from 0 to 7.")[m
[32m+[m[32m            print("Invalid option. Please choose from 0 to 8.")[m
             continue[m
 [m
         try:[m
[36m@@ -238,4 +75,4 @@[m [mdef main():[m
 [m
 [m
 if __name__ == "__main__":[m
[31m-    main()[m
\ No newline at end of file[m
[32m+[m[32m    main()[m
