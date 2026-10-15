import contextlib
import copy
import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from campusflow.history import display_ticket_history, get_ticket_history
from campusflow.operations import (
    assign_with_history, change_status_with_history, create_ticket_with_history,
)
from campusflow.sla import to_iso

T0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
CATEGORY = "network"   # must be a valid category in campusflow/tickets.py


def started_ticket():
    """One assigned, in_progress ticket plus its events."""
    tickets, events = [], []
    create_ticket_with_history(tickets, events, "Wifi down", CATEGORY,
                               "high", 12, "op1", now=T0)
    assign_with_history(tickets, events, "T001", "Sam", "op1", T0)
    change_status_with_history(tickets, events, "T001", "in_progress", "op1", T0)
    return tickets, events


class TestEventContent(unittest.TestCase):
    def test_start_event_records_before_after_and_actor(self):
        _, events = started_ticket()
        e = events[-1]
        self.assertEqual(e["event_type"], "START")
        self.assertEqual((e["before_status"], e["after_status"]),
                         ("open", "in_progress"))
        self.assertEqual((e["actor"], e["ticket_id"]), ("op1", "T001"))

    def test_reopen_keeps_created_at_and_earlier_events(self):
        tickets, events = started_ticket()
        change_status_with_history(tickets, events, "T001", "resolved", "op1", T0)
        old_events = copy.deepcopy(events)
        later = T0 + timedelta(hours=5)
        change_status_with_history(tickets, events, "T001", "open", "op1", later)
        self.assertEqual(tickets[0]["created_at"], to_iso(T0))
        self.assertEqual(events[:len(old_events)], old_events)
        self.assertEqual(events[-1]["event_type"], "REOPEN")


class TestRejectionsLeaveNoTrace(unittest.TestCase):
    def test_skip_to_resolved_changes_nothing(self):
        tickets, events = [], []
        create_ticket_with_history(tickets, events, "Wifi down", CATEGORY,
                                   "high", 12, "op1", now=T0)
        assign_with_history(tickets, events, "T001", "Sam", "op1", T0)
        snap_t, snap_e = copy.deepcopy(tickets), copy.deepcopy(events)
        with self.assertRaises(ValueError):
            change_status_with_history(tickets, events, "T001", "resolved", "op1", T0)
        self.assertEqual((tickets, events), (snap_t, snap_e))

    def test_assign_on_resolved_ticket_changes_nothing(self):
        tickets, events = started_ticket()
        change_status_with_history(tickets, events, "T001", "resolved", "op1", T0)
        snap_t, snap_e = copy.deepcopy(tickets), copy.deepcopy(events)
        with self.assertRaises(ValueError):
            assign_with_history(tickets, events, "T001", "Lee", "op1", T0)
        self.assertEqual((tickets, events), (snap_t, snap_e))

    def test_failed_event_write_rolls_back_assign(self):
        tickets, events = [], []
        create_ticket_with_history(tickets, events, "Wifi down", CATEGORY,
                                   "high", 12, "op1", now=T0)
        snap_t, snap_e = copy.deepcopy(tickets), copy.deepcopy(events)
        with mock.patch("campusflow.operations.record_event",
                        side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                assign_with_history(tickets, events, "T001", "Sam", "op1", T0)
        self.assertEqual((tickets, events), (snap_t, snap_e))


class TestHistoryDisplay(unittest.TestCase):
    def test_tied_timestamps_ordered_by_event_id(self):
        _, events = started_ticket()          # all three share timestamp T0
        history = get_ticket_history(list(reversed(events)), "T001")
        self.assertEqual([e["event_id"] for e in history],
                         ["E0001", "E0002", "E0003"])

    def test_display_prints_events_in_order(self):
        _, events = started_ticket()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            display_ticket_history(events, "t001")
        text = out.getvalue()
        self.assertLess(text.index("E0001"), text.index("E0002"))
        self.assertLess(text.index("E0002"), text.index("E0003"))

    def test_display_for_unknown_ticket_says_no_history(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            display_ticket_history([], "T999")
        self.assertIn("No history found", out.getvalue())


if __name__ == "__main__":
    unittest.main()