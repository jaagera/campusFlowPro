import unittest

from campusflow.duplicates import detect_duplicates, normalize_text


def make_ticket(ticket_id, title, category="Network", status="open"):
    return {"id": ticket_id, "title": title, "category": category, "status": status}


class TestDuplicates(unittest.TestCase):
    def setUp(self):
        self.tickets = [make_ticket("T001", " Wi-Fi   Down ")]

    def test_normalize_text(self):
        self.assertEqual(normalize_text("  Wi-Fi   DOWN "), "wi-fi down")

    def test_title_normalization_matches(self):
        result = detect_duplicates(self.tickets, "Network", "wi-fi down")
        self.assertEqual([t["id"] for t in result], ["T001"])

    def test_category_case_is_ignored(self):
        self.assertEqual(len(detect_duplicates(self.tickets, "network", "wi-fi down")), 1)

    def test_different_category_is_not_a_duplicate(self):
        self.assertEqual(detect_duplicates(self.tickets, "Hardware", "wi-fi down"), [])

    def test_resolved_ticket_is_ignored(self):
        self.tickets[0]["status"] = "resolved"
        self.assertEqual(detect_duplicates(self.tickets, "Network", "wi-fi down"), [])

    def test_in_progress_ticket_counts(self):
        self.tickets[0]["status"] = "in_progress"
        self.assertEqual(len(detect_duplicates(self.tickets, "Network", "wi-fi down")), 1)

    def test_detection_does_not_modify_tickets(self):
        before = [dict(t) for t in self.tickets]
        detect_duplicates(self.tickets, "Network", "wi-fi down")
        self.assertEqual(self.tickets, before)


if __name__ == "__main__":
    unittest.main()
