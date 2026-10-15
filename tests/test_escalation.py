
import copy
import unittest
from datetime import datetime, timedelta, timezone

from campusflow.sla import (
    escalate_overdue,
    init_ticket_sla,
    parse_iso,
    restart_sla_cycle,
)

START = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)
LATE = START + timedelta(minutes=61)


def make_ticket(ticket_id="T001", priority="critical", status="open"):
    ticket = {
        "id": ticket_id,
        "priority": priority,
        "status": status,
        "assigned_to": None,
    }
    init_ticket_sla(ticket, START)
    return ticket


class TestInitFields(unittest.TestCase):
    def test_init_sets_all_fields(self):
        ticket = make_ticket()
        self.assertEqual(parse_iso(ticket["created_at"]), START)
        self.assertEqual(parse_iso(ticket["updated_at"]), START)
        self.assertEqual(parse_iso(ticket["due_at"]), START + timedelta(minutes=60))
        self.assertEqual(ticket["escalation_cycle"], 0)
        self.assertIsNone(ticket["escalated_cycle"])


class TestEscalation(unittest.TestCase):
    def setUp(self):
        self.tickets = [make_ticket()]
        self.events = []

    def test_overdue_ticket_escalates_once(self):
        result = escalate_overdue(self.tickets, self.events, LATE, "ops")
        self.assertEqual(result["newly_escalated"], 1)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]["event_type"], "ESCALATE")
        self.assertEqual(self.events[0]["ticket_id"], "T001")

    def test_second_run_adds_no_event(self):
        escalate_overdue(self.tickets, self.events, LATE, "ops")
        escalate_overdue(self.tickets, self.events, LATE + timedelta(hours=3), "ops")
        self.assertEqual(len(self.events), 1)

    def test_second_run_reports_already_escalated(self):
        escalate_overdue(self.tickets, self.events, LATE, "ops")
        result = escalate_overdue(self.tickets, self.events, LATE, "ops")
        self.assertEqual(result["newly_escalated"], 0)
        self.assertEqual(result["already_escalated"], 1)

    def test_exactly_at_due_time_not_escalated(self):
        at_due = START + timedelta(minutes=60)
        result = escalate_overdue(self.tickets, self.events, at_due, "ops")
        self.assertEqual(result["newly_escalated"], 0)
        self.assertEqual(self.events, [])

    def test_resolved_ticket_not_escalated(self):
        self.tickets[0]["status"] = "resolved"
        escalate_overdue(self.tickets, self.events, LATE, "ops")
        self.assertEqual(self.events, [])

    def test_escalation_does_not_change_status_priority_or_assignee(self):
        escalate_overdue(self.tickets, self.events, LATE, "ops")
        ticket = self.tickets[0]
        self.assertEqual(ticket["status"], "open")
        self.assertEqual(ticket["priority"], "critical")
        self.assertIsNone(ticket["assigned_to"])

    def test_blank_actor_rejected_and_nothing_changes(self):
        before = copy.deepcopy(self.tickets)
        with self.assertRaises(ValueError):
            escalate_overdue(self.tickets, self.events, LATE, "   ")
        self.assertEqual(self.tickets, before)
        self.assertEqual(self.events, [])

    def test_event_ids_are_unique_and_increasing(self):
        self.tickets.append(make_ticket("T002"))
        escalate_overdue(self.tickets, self.events, LATE, "ops")
        ids = [e["event_id"] for e in self.events]
        self.assertEqual(ids, ["E0001", "E0002"])


class TestReopenCycle(unittest.TestCase):
    def setUp(self):
        self.tickets = [make_ticket()]
        self.events = []
        self.reopen_time = START + timedelta(hours=5)

    def test_reopen_restarts_due_and_keeps_created_at(self):
        ticket = self.tickets[0]
        ticket["status"] = "resolved"
        ticket["status"] = "open"
        restart_sla_cycle(ticket, self.reopen_time)
        self.assertEqual(parse_iso(ticket["created_at"]), START)
        self.assertEqual(
            parse_iso(ticket["due_at"]), self.reopen_time + timedelta(minutes=60)
        )
        self.assertEqual(ticket["escalation_cycle"], 1)

    def test_reopened_ticket_can_escalate_again(self):
        escalate_overdue(self.tickets, self.events, LATE, "ops")
        restart_sla_cycle(self.tickets[0], self.reopen_time)
        later = self.reopen_time + timedelta(minutes=61)
        result = escalate_overdue(self.tickets, self.events, later, "ops")
        self.assertEqual(result["newly_escalated"], 1)
        self.assertEqual(len(self.events), 2)

    def test_old_events_are_preserved_after_reopen(self):
        escalate_overdue(self.tickets, self.events, LATE, "ops")
        first_event = copy.deepcopy(self.events[0])
        restart_sla_cycle(self.tickets[0], self.reopen_time)
        self.assertEqual(self.events[0], first_event)


if __name__ == "__main__":
    unittest.main()
