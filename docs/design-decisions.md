# CampusFlow Pro: Design Decisions

## 1. Scope and ownership

CampusFlow Pro extends the original version 1 command-line interface (CLI). Version 1 was developed by Jacob Agera and Akpen Cyprian. Version 2 is being developed by Jacob Agera (Engineer A) and Favour Apochi Ogwa (Engineer B).

The objective is to introduce SLA management, escalation, audit history, persistence, queues, reporting, and other version 2 capabilities while preserving the original functionality and its tests.

Area

Owner

SLA rules, escalation, and ticket time fields

Engineer A — Jacob Agera

Version 2 storage and validation

Engineer A — Jacob Agera

Audit history, duplicate warnings, queues, metrics, and Knowledge Lab

Engineer B — Favour Apochi Ogwa

CLI integration (main.py, operations.py, test_cli.py)

Engineer A, subject to the team's agreed division of work

Ownership confirmation: Confirm with Favour that the CLI integration responsibilities reflect the team's agreement.

The team uses feature branches and pull requests to review changes before merging into main.


## 2. Layout and layering

main.py handles user input, menu navigation, and printing. Business rules belong in the appropriate business modules.

Business functions avoid calling print() or input(), allowing them to be tested directly.

operations.py integrates the original create_ticket, assign_ticket, and change_status functions with SLA fields and audit events. The original functions and their existing tests remain unchanged.

campusflow/queue.py shares its name with Python's standard-library queue module. Commands and tests should be run from the project root to preserve the intended import behavior.

This separation makes the application easier to test, maintain, and extend without mixing user interaction with business logic.



## 3. Time and SLA

All timestamps are timezone-aware UTC values and are stored as ISO 8601 strings with an explicit UTC offset.

Naive datetimes are rejected.

Time-dependent functions accept an injectable now argument, defaulting to the current UTC time. Tests use fixed timestamps instead of waiting for real time to pass.

SLA durations are determined by priority:

Priority

SLA duration

Critical

60 minutes

High

240 minutes

Medium

1,440 minutes

Low

2,880 minutes

The deadline is calculated using due_at = cycle_start + SLA duration.

A ticket is overdue only when the current time is strictly later than due_at and the ticket is not resolved. At the exact deadline, the ticket is not overdue.

created_at remains unchanged throughout the ticket's lifecycle.

Reopening a resolved ticket starts a new SLA cycle. The deadline is recalculated from the reopening time, and escalation_cycle increases.

The CLI accepts an optional operator-supplied UTC "as of" timestamp for escalation, queue, and report operations. This supports deterministic demonstrations and testing without waiting for a deadline to pass. Invalid and naive timestamps are rejected.

These decisions make SLA behavior predictable, consistent, and testable.

## 4. Escalation: idempotency approach

Chosen approach: cycle markers on tickets.

Each ticket stores escalation_cycle, which increases when a resolved ticket is reopened, and escalated_cycle, which records the cycle in which escalation last occurred.

A ticket is considered already escalated in the current cycle when these two values match.

Why this approach was selected:

It provides a straightforward check without scanning the complete event history.

The marker can be validated as part of ticket storage.

Reopening starts a new cycle, allowing another escalation without manually clearing the previous marker.

It makes the intended behavior easier to explain and test.

Rejected alternative: Searching the event history for an existing ESCALATE event for the same ticket and cycle. Although this avoids an additional ticket field, it requires examining historical events and depends on the event data accurately representing each cycle.

Trade-off: The marker introduces an additional field beyond the original requirements, but simplifies the idempotency check.

Escalation does not assign tickets or change their priority or status. It appends exactly one ESCALATE event for each eligible overdue ticket per cycle and reports the numbers of newly escalated and already-escalated tickets.

The escalated_in_current_cycle_count metric reads the ticket's escalated_cycle marker. An earlier implementation looked for a field on events that did not exist, causing the metric to return zero after a real escalation. This was corrected, and the updated test exercises escalation through the real function.

## 5. Audit history

Every successful CREATE, ASSIGN, START, RESOLVE, REOPEN, and ESCALATE operation appends an audit event containing:

event_id

ticket_id

event_type

actor

timestamp

before_status

after_status

details

Events are appended only after their associated operations succeed. In operations.py, the original operation runs first, followed by event recording. If event recording fails, a snapshot restores the ticket so that the ticket data and audit history do not remain inconsistent.

Rejected operations must not change tickets or append events.

The actor is an operator label entered at startup. It identifies the operator label associated with an action; it is not an authentication or authorization mechanism.

Event IDs follow the sequence E0001, E0002, and so on. record_event is the single event ID generator, and escalate_overdue uses it instead of generating event IDs independently.

The project currently has two functions named utc_now with different return types:

history.utc_now() returns an ISO-formatted string.

sla.utc_now() returns a timezone-aware datetime.

operations.py uses the SLA version because the SLA initialization function requires a datetime object.

Confirmation required: Discuss with Favour whether history.utc_now() should remain a string-returning function or be changed for consistency. Any change must account for existing callers and tests.

Existing audit events are not edited or deleted by normal CLI operations.

## 6. Duplicate warning

Duplicate detection normalizes ticket titles by trimming surrounding whitespace, applying case-folding, and collapsing repeated whitespace. Categories are trimmed and case-folded.

Only unresolved tickets with open or in_progress status are considered when checking for duplicates. A resolved ticket does not prevent the same problem from being reported again in the future.

When a possible duplicate is found, the CLI displays the matching ticket IDs and requests explicit confirmation before creating the new ticket. Declining the confirmation creates neither a ticket nor an audit event.

Duplicate detection is a warning rather than a silent deletion or automatic blocking mechanism.

The intended design keeps one active copy of the detection logic in reports.py.

Confirmation required: Check whether reports.py is the sole implementation in use and whether the duplicate implementation in duplicates.py has been removed, retained only for compatibility, or is still referenced elsewhere.

## 7. Persistence (schema version 2)

The application's state is stored in data/state.json using the following structure:

{
  "schema_version": 2,
  "tickets": [],
  "events": []
}

The actual arrays contain the application's ticket and audit event records.

Loading and validation

load_state validates the complete state before returning it. Validation covers required fields, data types, permitted statuses, timestamps, unique IDs, and references from events to existing tickets.

If the file does not exist, loading returns empty state.

If the file is malformed or fails validation, StorageError is raised.

Loading invalid data does not modify the stored file.

The CLI replaces its in-memory state only after loading succeeds, preserving the current valid state when loading fails.

Saving and file safety

save_state validates the data before writing. It writes to a temporary file in the same directory and then uses os.replace() to replace the main state file.

If writing fails before replacement, the original file remains intact and the temporary file is cleaned up.

Tickets and events are saved together through save_state. The separate event_storage.py module was removed to avoid maintaining two independent files that could disagree after a crash.

Data format and migration

JSON is parsed using Python's standard-library json module. eval() is not used to parse stored data.

Legacy list-style files are rejected without modification. Automatic migration from the legacy format is not implemented and remains an optional stretch goal.

Known limitation: due_at is not recomputed during loading to verify that it matches the cycle start and SLA duration, because the cycle start is not stored separately.
## 8. Queues and reports

The project maintains two distinct ticket queues.

Open Work Queue

The original queue remains unchanged. It displays open tickets ordered by priority and then by numeric ticket ID.

SLA Attention Queue

This queue includes both open and in_progress tickets. It sorts overdue tickets first, followed by ascending due_at, then ticket ID. Overdue tickets are clearly labelled.

Metrics

Reports are read-only and include:

Number of open tickets.

Number of in-progress tickets.

Number of resolved tickets.

Number of overdue unresolved tickets.

Number of tickets escalated in the current cycle.

Ticket counts grouped by priority.

Resolved tickets are excluded from overdue counts, even when their recorded deadlines are in the past.

## 9. Testing

The project uses Python's standard-library unittest framework. Tests use fixed UTC timestamps and temporary directories where appropriate so they can run without depending on real time or modifying production data.

The original version 1 tests are retained to protect existing behavior. The complete test suite must pass after integration and merging.

Negative testing is used to verify important rules by deliberately introducing a defect, confirming that the relevant test fails, and restoring the correct implementation. Only negative checks actually performed are reported as completed.


Before submission, run the full test suite from the project root and record its actual output. Do not substitute a guessed test count or report success if the suite has not completed successfully.

## 10. Git conventions

Branches follow the naming convention:

type/issue-number/description

Examples include feat/12-sla-engine and docs/20-engineer-a-documents, provided those names match the team's actual issue numbering and branch conventions.

The team follows these collaboration rules:

Each engineer works on a separate feature or documentation branch.

Changes are pushed to the appropriate remote feature branch.

Pull requests are used to propose changes to main.

The other engineer reviews and approves each pull request before it is merged.

Engineers do not approve their own pull requests.

Direct commits to main are avoided.

Reviewers run relevant tests and examine the proposed changes before approving a merge.

Each engineer authors at least two pull requests and reviews the other engineer's work.

The purpose of this workflow is to make changes traceable, reduce integration errors, and give both engineers experience with code review and collaborative software development.