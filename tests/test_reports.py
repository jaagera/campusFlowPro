
import unittest

from campusflow.reports import format_report, generate_report


def make_ticket(ticket_id, status="open", priority="low"):
    return {
        "id": ticket_id,
        "title": "Sample",
        "category": "Other",
        "urgency": "low",
        "affected_users": 1,
        "priority": priority,
        "status": status,
        "assigned_to": None,
    }


class TestGenerateReport(unittest.TestCase):
    def test_empty_list_gives_zero_report(self):
        report = generate_report([])
        self.assertEqual(report["total"], 0)
        self.assertEqual(sum(report["by_status"].values()), 0)
        self.assertEqual(sum(report["by_priority"].values()), 0)

    def test_total_counts_all_tickets(self):
        tickets = [make_ticket("T001"), make_ticket("T002"), make_ticket("T003")]
        self.assertEqual(generate_report(tickets)["total"], 3)

    def test_breakdown_by_status(self):
        tickets = [
            make_ticket("T001", status="open"),
            make_ticket("T002", status="open"),
            make_ticket("T003", status="in_progress"),
            make_ticket("T004", status="resolved"),
        ]
        by_status = generate_report(tickets)["by_status"]
        self.assertEqual(by_status["open"], 2)
        self.assertEqual(by_status["in_progress"], 1)
        self.assertEqual(by_status["resolved"], 1)

    def test_breakdown_by_priority(self):
        tickets = [
            make_ticket("T001", priority="critical"),
            make_ticket("T002", priority="high"),
            make_ticket("T003", priority="high"),
            make_ticket("T004", priority="low"),
        ]
        by_priority = generate_report(tickets)["by_priority"]
        self.assertEqual(by_priority["critical"], 1)
        self.assertEqual(by_priority["high"], 2)
        self.assertEqual(by_priority["medium"], 0)
        self.assertEqual(by_priority["low"], 1)

    def test_unused_categories_are_present_with_zero(self):
        report = generate_report([make_ticket("T001")])
        self.assertEqual(report["by_status"]["resolved"], 0)
        self.assertEqual(report["by_priority"]["critical"], 0)

    def test_breakdowns_add_up_to_total(self):
        tickets = [
            make_ticket("T001", status="open", priority="high"),
            make_ticket("T002", status="resolved", priority="medium"),
            make_ticket("T003", status="in_progress", priority="low"),
        ]
        report = generate_report(tickets)
        self.assertEqual(sum(report["by_status"].values()), report["total"])
        self.assertEqual(sum(report["by_priority"].values()), report["total"])

    def test_report_does_not_modify_tickets(self):
        tickets = [make_ticket("T001", status="open", priority="high")]
        before = [dict(t) for t in tickets]
        generate_report(tickets)
        self.assertEqual(tickets, before)


class TestFormatReport(unittest.TestCase):
    def test_format_shows_total_and_sections(self):
        text = format_report(generate_report([make_ticket("T001")]))
        self.assertIn("Total tickets: 1", text)
        self.assertIn("By status:", text)
        self.assertIn("By priority:", text)

    def test_format_empty_report(self):
        text = format_report(generate_report([]))
        self.assertIn("Total tickets: 0", text)
        self.assertIn("open: 0", text)


if __name__ == "__main__":
    unittest.main()

##NEW CODE
import unittest
from datetime import datetime, timedelta, timezone

from campusflow.reports import (
    detect_duplicates,
    is_ticket_overdue,
    normalize_title,
    sla_attention_queue,
    ticket_metrics,
)


class TestDuplicateDetection(unittest.TestCase):

    def setUp(self):
        self.tickets = [
            {
                "id": "T001",
                "title": " Wi-Fi   Down ",
                "category": "Network",
                "status": "open",
            },
            {
                "id": "T002",
                "title": "Wi-Fi Down",
                "category": "Network",
                "status": "resolved",
            },
        ]

    def test_title_normalization(self):
        self.assertEqual(
            normalize_title(" Wi-Fi   Down "),
            "wi-fi down",
        )

    def test_detects_unresolved_duplicate(self):
        result = detect_duplicates(
            "Network",
            "wi-fi down",
            self.tickets,
        )

        self.assertEqual([ticket["id"] for ticket in result], ["T001"])

    def test_different_category_is_not_duplicate(self):
        result = detect_duplicates(
            "Hardware",
            "wi-fi down",
            self.tickets,
        )

        self.assertEqual(result, [])

    def test_resolved_ticket_is_ignored(self):
        result = detect_duplicates(
            "Network",
            "Wi-Fi Down",
            self.tickets,
        )

        self.assertEqual([ticket["id"] for ticket in result], ["T001"])


class TestSLAAttentionQueue(unittest.TestCase):

    def setUp(self):
        self.now = datetime(
            2026, 10, 14, 12, 0,
            tzinfo=timezone.utc,
        )

        self.tickets = [
            {
                "id": "T003",
                "title": "Future ticket",
                "priority": "low",
                "status": "open",
                "due_at": (self.now + timedelta(hours=2)).isoformat(),
            },
            {
                "id": "T002",
                "title": "Overdue ticket",
                "priority": "high",
                "status": "in_progress",
                "due_at": (self.now - timedelta(minutes=10)).isoformat(),
            },
            {
                "id": "T001",
                "title": "Another overdue ticket",
                "priority": "critical",
                "status": "open",
                "due_at": (self.now - timedelta(minutes=20)).isoformat(),
            },
            {
                "id": "T004",
                "title": "Resolved ticket",
                "priority": "low",
                "status": "resolved",
                "due_at": (self.now - timedelta(hours=1)).isoformat(),
            },
        ]

    def test_overdue_ticket_is_overdue(self):
        self.assertTrue(
            is_ticket_overdue(self.tickets[1], self.now)
        )

    def test_exact_due_time_is_not_overdue(self):
        ticket = {
            "id": "T010",
            "status": "open",
            "due_at": self.now.isoformat(),
        }

        self.assertFalse(is_ticket_overdue(ticket, self.now))

    def test_resolved_ticket_is_never_overdue(self):
        self.assertFalse(
            is_ticket_overdue(self.tickets[3], self.now)
        )

    def test_overdue_tickets_appear_first(self):
        queue = sla_attention_queue(self.tickets, self.now)

        self.assertEqual(
            [ticket["id"] for ticket in queue],
            ["T001", "T002", "T003"],
        )

    def test_queue_excludes_resolved_tickets(self):
        queue = sla_attention_queue(self.tickets, self.now)

        self.assertNotIn(
            "T004",
            [ticket["id"] for ticket in queue],
        )

    def test_equal_due_dates_use_ticket_id_tiebreak(self):
        due = self.now - timedelta(minutes=5)

        tickets = [
            {
                "id": "T003",
                "status": "open",
                "due_at": due.isoformat(),
            },
            {
                "id": "T001",
                "status": "open",
                "due_at": due.isoformat(),
            },
            {
                "id": "T002",
                "status": "open",
                "due_at": due.isoformat(),
            },
        ]

        queue = sla_attention_queue(tickets, self.now)

        self.assertEqual(
            [ticket["id"] for ticket in queue],
            ["T001", "T002", "T003"],
        )


class TestTicketMetrics(unittest.TestCase):

    def test_counts_ticket_statuses_and_priorities(self):
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)

        tickets = [
            {
                "id": "T001",
                "status": "open",
                "priority": "critical",
                "due_at": (now - timedelta(minutes=1)).isoformat(),
                "escalation_cycle": 0,
                "escalated_cycle": 0,
            },
            {
                "id": "T002",
                "status": "in_progress",
                "priority": "high",
                "due_at": (now + timedelta(hours=1)).isoformat(),
                "escalation_cycle": 0,
            },
            {
                "id": "T003",
                "status": "resolved",
                "priority": "low",
                "due_at": (now - timedelta(hours=1)).isoformat(),
                "escalation_cycle": 0,
            },
        ]

        events = [
            {
                "ticket_id": "T001",
                "event_type": "ESCALATE",
                "escalation_cycle": 0,
            }
        ]

        result = ticket_metrics(tickets, events, now)

        self.assertEqual(result["open_count"], 1)
        self.assertEqual(result["in_progress_count"], 1)
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(result["overdue_unresolved_count"], 1)
        self.assertEqual(
            result["escalated_in_current_cycle_count"], 1
        )
        self.assertEqual(result["priority_counts"]["critical"], 1)
        self.assertEqual(result["priority_counts"]["high"], 1)
        self.assertEqual(result["priority_counts"]["low"], 1)


if __name__ == "__main__":
    unittest.main()