import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

from campusflow.sla import init_ticket_sla
from campusflow.storage import StorageError, load_state, save_state

START = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)


def make_ticket(ticket_id="T001"):
    ticket = {
        "id": ticket_id,
        "title": "Campus Wi-Fi is down",
        "category": "Network",
        "urgency": "high",
        "affected_users": 15,
        "priority": "critical",
        "status": "open",
        "assigned_to": None,
    }
    init_ticket_sla(ticket, START)
    return ticket


def make_event(event_id="E001", ticket_id="T001"):
    return {
        "event_id": event_id,
        "ticket_id": ticket_id,
        "event_type": "CREATE",
        "actor": "ops",
        "timestamp": "2026-10-14T10:00:00+00:00",
        "before_status": None,
        "after_status": "open",
        "details": "created",
    }


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = os.path.join(self.temp_dir.name, "state.json")

    def read_raw(self):
        with open(self.path, "r", encoding="utf-8") as handle:
            return handle.read()

    def write_raw(self, text):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(text)


class TestSaveAndLoad(StateTestCase):
    def test_round_trip_preserves_tickets_and_events(self):
        tickets, events = [make_ticket()], [make_event()]
        save_state(tickets, events, self.path)
        self.assertEqual(load_state(self.path), (tickets, events))

    def test_saved_file_has_schema_version_2(self):
        save_state([make_ticket()], [make_event()], self.path)
        self.assertEqual(json.loads(self.read_raw())["schema_version"], 2)

    def test_missing_file_gives_empty_state(self):
        self.assertEqual(load_state(self.path), ([], []))

    def test_none_values_survive_round_trip(self):
        save_state([make_ticket()], [], self.path)
        ticket = load_state(self.path)[0][0]
        self.assertIsNone(ticket["assigned_to"])
        self.assertIsNone(ticket["escalated_cycle"])

    def test_no_temp_files_left_after_save(self):
        save_state([make_ticket()], [], self.path)
        self.assertEqual(os.listdir(self.temp_dir.name), ["state.json"])


class TestRejectedFiles(StateTestCase):
    def test_corrupt_json_raises_and_file_untouched(self):
        self.write_raw("{ broken json")
        with self.assertRaises(StorageError):
            load_state(self.path)
        self.assertEqual(self.read_raw(), "{ broken json")

    def test_legacy_list_file_rejected_and_untouched(self):
        self.write_raw('[{"id": "T001"}]')
        with self.assertRaises(StorageError):
            load_state(self.path)
        self.assertEqual(self.read_raw(), '[{"id": "T001"}]')

    def test_wrong_schema_version_rejected(self):
        self.write_raw(json.dumps({"schema_version": 1, "tickets": [], "events": []}))
        with self.assertRaises(StorageError):
            load_state(self.path)

    def test_missing_ticket_field_rejected(self):
        ticket = make_ticket()
        del ticket["due_at"]
        self.write_raw(json.dumps(
            {"schema_version": 2, "tickets": [ticket], "events": []}))
        with self.assertRaises(StorageError):
            load_state(self.path)

    def test_duplicate_ticket_id_rejected(self):
        self.write_raw(json.dumps({
            "schema_version": 2,
            "tickets": [make_ticket(), make_ticket()],
            "events": [],
        }))
        with self.assertRaises(StorageError):
            load_state(self.path)

    def test_event_for_unknown_ticket_rejected(self):
        self.write_raw(json.dumps({
            "schema_version": 2,
            "tickets": [make_ticket()],
            "events": [make_event(ticket_id="T999")],
        }))
        with self.assertRaises(StorageError):
            load_state(self.path)

    def test_naive_timestamp_rejected(self):
        ticket = make_ticket()
        ticket["created_at"] = "2026-10-14T10:00:00"
        self.write_raw(json.dumps(
            {"schema_version": 2, "tickets": [ticket], "events": []}))
        with self.assertRaises(StorageError):
            load_state(self.path)

    def test_in_progress_ticket_must_be_assigned(self):
        ticket = make_ticket()
        ticket["status"] = "in_progress"
        self.write_raw(json.dumps(
            {"schema_version": 2, "tickets": [ticket], "events": []}))
        with self.assertRaises(StorageError):
            load_state(self.path)


class TestSafety(StateTestCase):
    def test_saving_invalid_state_refuses_and_keeps_old_file(self):
        save_state([make_ticket()], [], self.path)
        good_text = self.read_raw()
        broken = make_ticket("T002")
        del broken["status"]
        with self.assertRaises(StorageError):
            save_state([make_ticket(), broken], [], self.path)
        self.assertEqual(self.read_raw(), good_text)

    def test_failed_write_keeps_old_file_and_leaves_no_temp(self):
        save_state([make_ticket()], [], self.path)
        good_text = self.read_raw()
        with mock.patch("campusflow.storage.os.replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                save_state([make_ticket(), make_ticket("T002")], [], self.path)
        self.assertEqual(self.read_raw(), good_text)
        self.assertEqual(os.listdir(self.temp_dir.name), ["state.json"])

    def test_failed_load_does_not_change_callers_state(self):
        tickets, events = [make_ticket()], [make_event()]
        snapshot = copy.deepcopy((tickets, events))
        self.write_raw("{ broken json")
        try:
            tickets, events = load_state(self.path)
        except StorageError:
            pass
        self.assertEqual((tickets, events), snapshot)


if __name__ == "__main__":
    unittest.main()
