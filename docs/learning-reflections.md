# Learning Reflections: Engineer A (Jacob Agera)

## My Knowledge Lab result

Participant: A — Jacob Agera

Score: 10

Session record saved at: ACTUAL PATH OF MY SAVED JSON SESSION FILE>

Topics flagged for revision: By Priority


## Reflection on one missed or difficult question

Question: Q6 — Handling corrupted JSON during state loading.

I first believed...

I initially thought that if the application encountered corrupted JSON, it might return an empty list or replace the existing in-memory data with empty data. I was not fully sure how the storage layer distinguished between a missing file and a file containing invalid data.

**I checked...**
I reviewed the storage requirements and the behavior of load_state in the version 2 storage implementation. I also examined the storage tests, particularly test_failed_load_does_not_change_callers_state, and the checkpoint output showing that a corrupt file was rejected while the existing in-memory ticket data was preserved.

**I changed my understanding because...**
I learned that a missing state file and a corrupted state file must be handled differently. A missing file can result in an empty initial state, while malformed or invalid data should raise StorageError. The application must not replace its existing valid in-memory state unless loading succeeds. This taught me the importance of validating data before changing application state.

## Prompts if you get stuck

These are prompts for your thinking, not answers.

- Q1 (due vs overdue): which comparison operator does `is_overdue` use, and which test proves it?
- Q5 (repeated escalation): how do `escalation_cycle` and `escalated_cycle` stop a second event within one cycle?
- Q6 (corrupt JSON): what does `load_state` return or raise, and what happens to the data already in memory?
- Q10 (audit log): in `change_status_with_history`, which line runs first, the status change or `record_event`, and what happens to the event count if the change raises?

## A tiny code or test demonstration I can give a mentor

I will run the SLA unit tests from the project root:

python3 -m unittest tests.test_sla -v

I will point out these two tests:

test_critical_at_exactly_60_minutes_is_not_overdue

test_critical_at_61_minutes_is_overdue

I will explain that a critical ticket is not overdue when the current time is exactly equal to its deadline, but becomes overdue when the current time is later than the deadline. This demonstrates why the implementation uses a strict > comparison rather than >=.

I will use the actual test output during the demonstration and report any failures honestly.

## Design mistake (for the submission form)

What I believed:

I believed that the escalated_in_current_cycle_count metric was correct because its original unit test passed. I assumed that a passing test meant the metric accurately represented what happened in the real application.

What the evidence showed:

The metric was looking for an escalation_cycle field on event records, but the actual events did not contain that field. As a result, the report returned zero even after a real escalation. The original test passed because it manually created an event with the expected field instead of using the actual event structure.

What I changed:

I changed the metric to read the ticket's escalated_cycle marker and updated the test to exercise escalation through the real function. This taught me to verify that tests reflect the application's actual data structures and behavior, rather than relying only on a passing test result.