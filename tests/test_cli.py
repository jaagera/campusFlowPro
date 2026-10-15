import contextlib
import io
import unittest
from datetime import datetime, timezone
from unittest import mock

import main
from campusflow.reports import ticket_metrics


def run(handler, *args, inputs=()):
    """Call a CLI handler with scripted input and swallow its printing."""
    with mock.patch("builtins.input", side_effect=list(inputs)):
        with contextlib.redirect_stdout(io.StringIO()):
            return handler(*args)


def create_inputs(title="Wi-Fi Down", category="Network", urgency="high", users="15"):
    return [title, category, urgency, users]


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tickets, self.events = [], []

    def create(self, *inputs):
        return run(main.create_new_ticket, self.tickets, self.events, "ops",
                   inputs=inputs)

    def test_valid_create_records_ticket_and_event(self):
        self.assertTrue(self.create(*create_inputs()))
        self.assertEqual(len(self.tickets), 1)
        self.assertEqual([e["event_type"] for e in self.events], ["CREATE"])

    def test_invalid_input_creates_nothing(self):
        self.assertFalse(self.create(*create_inputs(users="0")))
        self.assertEqual((self.tickets, self.events), ([], []))

    def test_declining_duplicate_creates_neither_ticket_nor_event(self):
        self.create(*create_inputs(title=" Wi-Fi   Down "))
        changed = self.create(*create_inputs(title="wi-fi down"), "n")
        self.assertFalse(changed)
        self.assertEqual(len(self.tickets), 1)
        self.assertEqual(len(self.events), 1)

    def test_confirming_duplicate_creates_second_ticket(self):
        self.create(*create_inputs(title=" Wi-Fi   Down "))
        self.assertTrue(self.create(*create_inputs(title="wi-fi down"), "y"))
        self.assertEqual(len(self.tickets), 2)

    def test_illegal_transition_appends_no_event(self):
        self.create(*create_inputs())
        changed = run(main.update_ticket_status, self.tickets, self.events, "ops",
                      inputs=["T001", "in_progress"])
        self.assertFalse(changed)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.tickets[0]["status"], "open")

    def test_escalation_runs_once_even_when_repeated(self):
        self.create(*create_inputs())
        future = "2099-01-01T00:00:00+00:00"
        first = run(main.check_escalations, self.tickets, self.events, "ops",
                    inputs=[future])
        second = run(main.check_escalations, self.tickets, self.events, "ops",
                     inputs=[future])
        self.assertTrue(first)
        self.assertFalse(second)
        kinds = [e["event_type"] for e in self.events]
        self.assertEqual(kinds.count("ESCALATE"), 1)

    def test_escalated_metric_counts_after_escalation(self):
        self.create(*create_inputs())
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        run(main.check_escalations, self.tickets, self.events, "ops",
            inputs=[future.isoformat()])
        metrics = ticket_metrics(self.tickets, self.events, future)
        self.assertEqual(metrics["escalated_in_current_cycle_count"], 1)

    def test_as_of_time_rejects_naive_and_garbage_then_accepts_valid(self):
        result = run(main.ask_as_of_time, inputs=[
            "2026-10-14T12:00:00", "not a time", "2026-10-14T12:00:00+00:00"])
        self.assertEqual(result, datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc))

    def test_blank_operator_label_is_reprompted(self):
        self.assertEqual(run(main.ask_operator, inputs=["", "   ", "ops"]), "ops")


if __name__ == "__main__":
    unittest.main()
