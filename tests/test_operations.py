import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from campusflow.operations import (
    assign_with_history,
    change_status_with_history,
    create_ticket_with_history,
)
from campusflow.sla import parse_iso

T0 = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)


def later(minutes):
    return T0 + timedelta(minutes=minutes)


class OperationsTestCase(unittest.TestCase):
    def setUp(self):
        self.tickets = []
        self.events = []

    def create(self, title="Campus Wi-Fi is down", category="Network",
               urgency="high", users=15, confirm=None, actor="ops", now=T0):
        return create_ticket_with_history(
            self.tickets, self.events, title, category, urgency, users,
            actor, now=now, confirm_duplicate=confirm)

    def types(self):
        return [event["event_type"] for event in self.events]


class TestCreate(OperationsTestCase):
    def test_create_records_create_event(self):
        ticket = self.create()
        self.assertEqual(self.types(), ["CREATE"])
        self.assertIsNone(self.events[0]["before_status"])
        self.assertEqual(self.events[0]["after_status"], "open")
        self.assertEqual(self.events[0]["ticket_id"], ticket["id"])

    def test_invalid_input_creates_nothing(self):
        with self.assertRaises(ValueError):
            self.create(users=0)
        self.assertEqual(self.tickets, [])
        self.assertEqual(self.events, [])

    def test_blank_actor_creates_nothing(self):
        with self.assertRaises(ValueError):
            self.create(actor="   ")
        self.assertEqual((self.tickets, self.events), ([], []))

    def test_duplicate_declined_creates_nothing(self):
        self.create(title=" Wi-Fi   Down ")
        result = self.create(title="wi-fi down", confirm=lambda matches: False)
        self.assertIsNone(result)
        self.assertEqual(len(self.tickets), 1)
        self.assertEqual(len(self.events), 1)

    def test_duplicate_without_callback_is_declined(self):
        self.create(title="Wi-Fi down")
        self.assertIsNone(self.create(title="wi-fi down"))
        self.assertEqual(len(self.tickets), 1)

    def test_duplicate_confirmed_creates_second_ticket(self):
        first = self.create(title=" Wi-Fi   Down ")
        shown = []
        second = self.create(
            title="wi-fi down",
            confirm=lambda matches: shown.append([m["id"] for m in matches]) or True)
        self.assertEqual(shown, [[first["id"]]])
        self.assertIsNotNone(second)
        self.assertEqual(len(self.tickets), 2)
        self.assertEqual(self.types(), ["CREATE", "CREATE"])

    def test_resolved_match_does_not_warn(self):
        first = self.create(title="Wi-Fi down")
        first["status"] = "resolved"
        shown = []
        self.create(title="wi-fi down",
                    confirm=lambda matches: shown.append(matches) or True)
        self.assertEqual(shown, [])
        self.assertEqual(len(self.tickets), 2)

    def test_failed_event_rolls_back_ticket(self):
        with mock.patch("campusflow.operations.record_event",
                        side_effect=ValueError("boom")):
            with self.assertRaises(ValueError):
                self.create()
        self.assertEqual((self.tickets, self.events), ([], []))


class TestAssignAndStatus(OperationsTestCase):
    def setUp(self):
        super().setUp()
        self.ticket = self.create()
        self.tid = self.ticket["id"]

    def test_assign_records_event(self):
        assign_with_history(self.tickets, self.events, self.tid, "Ada", "ops", later(5))
        self.assertEqual(self.types(), ["CREATE", "ASSIGN"])

    def test_unknown_ticket_appends_no_event(self):
        with self.assertRaises(ValueError):
            assign_with_history(self.tickets, self.events, "T999", "Ada", "ops", later(5))
        self.assertEqual(len(self.events), 1)

    def test_illegal_transition_appends_no_event(self):
        with self.assertRaises(ValueError):
            change_status_with_history(
                self.tickets, self.events, self.tid, "in_progress", "ops", later(5))
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.ticket["status"], "open")

    def test_full_lifecycle_event_sequence_and_new_sla_cycle(self):
        assign_with_history(self.tickets, self.events, self.tid, "Ada", "ops", later(5))
        for minutes, status in ((10, "in_progress"), (20, "resolved"), (50, "open")):
            change_status_with_history(
                self.tickets, self.events, self.tid, status, "ops", later(minutes))
        self.assertEqual(
            self.types(), ["CREATE", "ASSIGN", "START", "RESOLVE", "REOPEN"])
        self.assertEqual(parse_iso(self.ticket["created_at"]), T0)
        self.assertEqual(
            parse_iso(self.ticket["due_at"]), later(50) + timedelta(minutes=60))

    def test_failed_event_rolls_back_status_change(self):
        assign_with_history(self.tickets, self.events, self.tid, "Ada", "ops", later(5))
        with mock.patch("campusflow.operations.record_event",
                        side_effect=ValueError("boom")):
            with self.assertRaises(ValueError):
                change_status_with_history(
                    self.tickets, self.events, self.tid, "in_progress", "ops", later(10))
        self.assertEqual(self.ticket["status"], "open")
        self.assertEqual(len(self.events), 2)

    def test_blank_actor_changes_nothing(self):
        with self.assertRaises(ValueError):
            assign_with_history(self.tickets, self.events, self.tid, "Ada", "  ", later(5))
        self.assertIsNone(self.ticket["assigned_to"])
        self.assertEqual(len(self.events), 1)


if __name__ == "__main__":
    unittest.main()
