
import unittest
from datetime import datetime, timedelta, timezone

from campusflow.sla import (
    calculate_due_at,
    is_overdue,
    parse_iso,
    start_sla_cycle,
    to_iso,
)

START = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)


def make_ticket(priority="critical", status="open"):
    ticket = {"id": "T001", "priority": priority, "status": status}
    start_sla_cycle(ticket, START)
    return ticket


class TestDueAt(unittest.TestCase):
    def test_thresholds_per_priority(self):
        expected = {"critical": 60, "high": 240, "medium": 1440, "low": 2880}
        for priority, minutes in expected.items():
            self.assertEqual(
                calculate_due_at(priority, START), START + timedelta(minutes=minutes)
            )

    def test_unknown_priority_rejected(self):
        with self.assertRaises(ValueError):
            calculate_due_at("urgent", START)

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            calculate_due_at("low", datetime(2026, 10, 14, 10, 0))

    def test_iso_round_trip_keeps_timezone(self):
        text = to_iso(START)
        self.assertEqual(parse_iso(text), START)
        self.assertTrue(text.endswith("+00:00"))


class TestOverdue(unittest.TestCase):
    def test_critical_at_exactly_60_minutes_is_not_overdue(self):
        ticket = make_ticket()
        self.assertFalse(is_overdue(ticket, START + timedelta(minutes=60)))

    def test_critical_at_61_minutes_is_overdue(self):
        ticket = make_ticket()
        self.assertTrue(is_overdue(ticket, START + timedelta(minutes=61)))

    def test_resolved_ticket_is_never_overdue(self):
        ticket = make_ticket(status="resolved")
        self.assertFalse(is_overdue(ticket, START + timedelta(days=30)))

    def test_in_progress_ticket_can_be_overdue(self):
        ticket = make_ticket(status="in_progress")
        self.assertTrue(is_overdue(ticket, START + timedelta(minutes=61)))

    def test_low_priority_not_overdue_after_61_minutes(self):
        ticket = make_ticket(priority="low")
        self.assertFalse(is_overdue(ticket, START + timedelta(minutes=61)))

    def test_is_overdue_does_not_modify_ticket(self):
        ticket = make_ticket()
        before = dict(ticket)
        is_overdue(ticket, START + timedelta(minutes=90))
        self.assertEqual(ticket, before)


if __name__ == "__main__":
    unittest.main()