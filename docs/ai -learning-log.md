# AI Learning Log: Engineer A (Jacob Agera)

## Cycle 1: Timezone-aware UTC and an injected clock
(i) Confusion/question:

My SLA rule says a critical ticket is overdue only when the current time is strictly later than its due_at time. I did not know how to test the exact 60-minute boundary without waiting an hour. I also wanted to understand why using datetime.now() directly inside a function could make testing difficult.

(ii) AI explanation:

I learned that naive datetimes do not contain timezone information, while timezone-aware datetimes do. Comparing them can cause errors. Using datetime.now() directly inside business logic also makes tests depend on the actual time. Passing a fixed now value into a function makes it possible to test different time scenarios consistently. Using UTC helps keep time comparisons consistent.

(iii) My mini-experiment:

I experimented with creating a timezone-aware UTC datetime and adding 60 minutes to it. I predicted that a critical ticket would not be overdue when the current time was exactly equal to its deadline, but would become overdue when the current time moved one minute beyond the deadline. My checkpoint results confirmed this expectation.

(iv) Evidence:

My checkpoint script printed:

A1  critical at 60 min overdue? False
A2  critical at 61 min overdue? True

Unit tests: test_critical_at_exactly_60_minutes_is_not_overdue and test_critical_at_61_minutes_is_overdue in tests/test_sla.py.

Negative check: Not documented here because I have not confirmed that I deliberately changed > to >=, observed the failure, and restored the original operator.

(v) Decision:

Accepted. The is_overdue(ticket, now=None) function uses the strict > comparison, and calculate_due_at rejects naive datetimes. This keeps the SLA rule clear and makes time-dependent behavior easier to test.


What I can now explain without AI:

A ticket becomes overdue when the current time is later than its deadline, not when both times are exactly equal. UTC provides a consistent time reference, while injecting now allows me to test different times without waiting for the real clock.


## Cycle 2: Idempotent escalation (one event per SLA cycle)

(i) Confusion/question:

I needed the system to check overdue tickets repeatedly without creating duplicate escalation events. However, when a ticket is reopened, it should be possible for the system to escalate it again if it becomes overdue in the new cycle.

(ii) AI explanation:

I learned that idempotency means repeating an operation should not produce duplicate side effects when nothing relevant has changed. A cycle marker can help enforce this rule. The ticket stores an escalation_cycle value that increases when it is reopened and an escalated_cycle value that records the cycle in which escalation occurred. If both values match, the ticket has already been escalated during that cycle.

(iii) My mini-experiment:

I used the escalation checkpoint to examine what happens when the escalation operation runs more than once. I expected the first run to create an escalation event and the second run to create no additional event for the same cycle. The checkpoint showed one new event on the first run and zero new events on the second run. The results also showed that the ticket's creation time remained unchanged while its deadline reflected the new value.

(iv) Evidence:

My checkpoint script printed:

A3  run 1 new: 1 | run 2 new: 0 | ESCALATE events: 1
A4  created_at unchanged: True | new due_at: 2026-10-14T16:00:00+00:00

Tests: test_second_run_adds_no_event and test_reopened_ticket_can_escalate_again in tests/test_escalation.py, and test_escalation_runs_once_even_when_repeated in tests/test_cli.py.

Negative check: Not documented here because I have not confirmed that I removed the already-escalated branch, observed the test failure, and restored it.

(v) Decision:

Accepted. I chose the marker approach instead of scanning all events to determine whether a ticket had already been escalated. Although it adds an extra field, it makes the check straightforward and can be validated when saving and loading ticket data.

What I can now explain without AI:

The system compares the ticket's current escalation cycle with the cycle in which it was last escalated. When the values match, it does not create another escalation event. Reopening the ticket starts a new cycle, allowing another escalation when the SLA conditions are met.


## Cycle 3: Atomic writes and validating before replacing memory

(i) Confusion/question:

I wanted to understand what could happen if the application crashed while saving data or if a JSON file became corrupted. My main concern was preventing invalid data from replacing valid data in the file or in memory.

(ii) AI explanation:

I learned that writing directly to the main file can put existing data at risk if the write fails partway through. A safer approach is to write to a temporary file in the same directory and then use os.replace() to replace the original file after the temporary file has been written successfully. I also learned to validate loaded data before returning it to the application, use the standard-library json module for JSON processing, and avoid using eval() on stored data.

(iii) My mini-experiment:

I examined the storage checkpoint results for successful saving, invalid save data, and corrupted JSON. The experiment showed that invalid save data was refused without damaging the existing good file. It also showed that a corrupted file was rejected and the caller's existing in-memory ticket data remained available. These results helped me understand why validation should happen before replacing existing data.

(iv) Evidence:

My checkpoint script printed:

A5  restart restored: 1 ticket(s), 2 event(s)
A6  invalid save refused; good file untouched: True | temp files left: []
A5  corrupt file rejected; file untouched: True | memory kept: 1 ticket(s)

Tests in tests/test_state_storage.py, including test_failed_write_keeps_old_file_and_leaves_no_temp and test_failed_load_does_not_change_callers_state.

Negative check: Not documented here because I have not confirmed that I deliberately changed the implementation to write directly to the main file, observed the test failure, and restored the safer approach.

(v) Decision:

Accepted. load_state validates the loaded state and raises StorageError when the data is invalid. save_state validates data before writing. A legacy list file is rejected without being modified, protecting the application from silently accepting an unexpected storage format.


What I can now explain without AI:

If a program writes directly to its main data file and fails during the write, the original contents may be damaged or incomplete. Writing to a temporary file first helps preserve the original until the replacement is ready. Validating data before returning it also prevents corrupted information from replacing the application's current in-memory state.

## Cycle 4: Advice I Corrected Because of Evidence

(i) Confusion/question:

Menu option 1 needed to create a ticket using the current time. I initially assumed that the integrated operations.py implementation was correct because its existing tests passed.

(ii) AI suggestion:

The suggested implementation imported utc_now from history.py into operations.py. However, the function in history.py returned a string rather than a datetime object.

(iii) My experiment:

I wrote CLI tests that created a ticket without explicitly passing a time. This allowed me to test the default execution path instead of relying only on tests that supplied a time manually.

(iv) Evidence:

The tests failed with:

AttributeError: 'str' object has no attribute 'tzinfo'

I ran grep -n "def utc_now" -A3 campusflow/history.py and found that the function returned datetime.now(timezone.utc).isoformat(), which produces a string. However, init_ticket_sla needed a datetime object.

The earlier test_operations.py tests always supplied an explicit now value, so they did not exercise the broken default path.

(v) Decision:

Changed. operations.py now imports utc_now from sla.py, which returns a datetime object. The CLI tests now cover the default path, helping catch problems that tests with explicit arguments might miss.

What I can now explain without AI:

A test can pass even when a function's default behavior is broken if the test always supplies the missing value manually. Testing the default path helps reveal integration problems that would otherwise appear only when a real user runs the application through the CLI.

## Design Mistake and How Evidence Changed My Thinking

Selected mistake: Old metric and its test agreed with each other but not with reality.

What I believed:

I believed that escalated_in_current_cycle_count was correctly measuring escalated tickets because its test passed. I initially trusted the test result without checking whether the test data represented the actual structure of escalation events.

What the evidence showed:

The metric searched for an escalation_cycle field on event records, but the actual events did not contain that field. As a result, the report returned zero even after a real escalation. The original test passed because it manually created an event containing the expected field, making the test inconsistent with the real application data.

What I changed:

I changed the metric to read the ticket's escalated_cycle marker instead of looking for a nonexistent field on the event. I also updated the test to reflect the actual data structure. This taught me to verify that tests represent real application behavior rather than simply confirming that my implementation and test agree with each other.

My main lesson:

Passing tests are useful evidence, but they are not proof that a feature is correct. I need to understand the data model, test realistic scenarios, and compare the program's output with the behavior the requirements actually expect.





