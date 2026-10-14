"""Interactive Engineering Knowledge Lab for CampusFlow."""

import json
from datetime import datetime, timezone
from pathlib import Path


QUESTIONS = [
    {
        "topic": "SLA boundaries",
        "question": (
            "A critical ticket is created at 10:00 UTC. "
            "At 11:00 UTC, is it overdue?"
        ),
        "options": {
            "A": "Yes",
            "B": "No, only strictly after 11:00",
            "C": "Only if assigned",
            "D": "Only if reopened",
        },
        "answer": "B",
    },
    {
        "topic": "Priority rules",
        "question": (
            "Urgency is low and affected_users is 10. "
            "What is the priority?"
        ),
        "options": {
            "A": "Critical",
            "B": "High",
            "C": "Medium",
            "D": "Low",
        },
        "answer": "B",
    },
    {
        "topic": "State invariants",
        "question": (
            "An unassigned open ticket moves directly "
            "to in_progress. What should happen?"
        ),
        "options": {
            "A": "Transition succeeds",
            "B": "Status changes but history stays",
            "C": "Reject without changing ticket or events",
            "D": "Delete the ticket",
        },
        "answer": "C",
    },
    {
        "topic": "SLA reopening",
        "question": (
            "A resolved high-priority ticket is reopened. "
            "Which SLA behavior is correct?"
        ),
        "options": {
            "A": "Keep the old due_at always",
            "B": "Start a fresh SLA cycle while preserving created_at",
            "C": "Reset created_at",
            "D": "Delete previous events",
        },
        "answer": "B",
    },
    {
        "topic": "Idempotency",
        "question": (
            "An overdue ticket is checked three times "
            "within one SLA cycle. How many new ESCALATE events?"
        ),
        "options": {
            "A": "Three",
            "B": "Two",
            "C": "One",
            "D": "Zero",
        },
        "answer": "C",
    },
    {
        "topic": "Safe JSON loading",
        "question": (
            "The saved file contains invalid JSON. "
            "What is the safest action?"
        ),
        "options": {
            "A": "Replace data with an empty list",
            "B": "Use eval()",
            "C": "Continue with partial data",
            "D": "Reject the load and preserve existing valid state",
        },
        "answer": "D",
    },
    {
        "topic": "Code review",
        "question": (
            "A pull request changes SLA calculations "
            "but adds no boundary tests. What should a reviewer do?"
        ),
        "options": {
            "A": "Approve because it runs locally",
            "B": "Request focused tests and an explanation",
            "C": "Merge and test next week",
            "D": "Ask AI to approve automatically",
        },
        "answer": "B",
    },
    {
        "topic": "Responsible AI use",
        "question": (
            "An assistant suggests using eval() to parse JSON. "
            "What should you do?"
        ),
        "options": {
            "A": "Copy the suggestion",
            "B": "Disable tests",
            "C": "Reject it and use JSON parsing with validation",
            "D": "Share the entire file publicly",
        },
        "answer": "C",
    },
    {
        "topic": "Duplicate detection",
        "question": (
            "Two unresolved tickets have titles "
            "' Wi-Fi   Down ' and 'wi-fi down' in the same category. "
            "What should the CLI do?"
        ),
        "options": {
            "A": "Silently delete the original",
            "B": "Warn and require confirmation",
            "C": "Silently block the new ticket forever",
            "D": "Ignore normalization",
        },
        "answer": "B",
    },
    {
        "topic": "Audit history",
        "question": (
            "An invalid status operation is rejected. "
            "What should happen to the event count?"
        ),
        "options": {
            "A": "Increase by one",
            "B": "Increase twice",
            "C": "Reset to zero",
            "D": "Stay unchanged",
        },
        "answer": "D",
    },
]


def score_answers(answers):
    """Return the number of correct answers."""

    return sum(
        answer == question["answer"]
        for answer, question in zip(answers, QUESTIONS)
    )


def ask_valid_choice(input_func=input):
    """Accept only A, B, C or D."""

    while True:
        choice = input_func("Choose A, B, C or D: ").strip().upper()

        if choice in {"A", "B", "C", "D"}:
            return choice

        print("Invalid answer. Please enter A, B, C or D.")


def run_knowledge_lab(
    input_func=input,
    output_func=print,
    session_directory=Path("data/learning_sessions"),
):
    """Run the quiz and save a learning session."""

    participant = ""

    while participant not in {"A", "B"}:
        participant = input_func(
            "Choose participant (A or B): "
        ).strip().upper()

        if participant not in {"A", "B"}:
            output_func("Invalid participant. Enter A or B.")

    answers = []
    explanations = {}

    for index, question in enumerate(QUESTIONS, start=1):
        output_func(f"\nQuestion {index}/10")
        output_func(f"Topic: {question['topic']}")
        output_func(question["question"])

        for letter, option in question["options"].items():
            output_func(f"{letter}. {option}")

        answer = ask_valid_choice(input_func)
        answers.append(answer)

        explanation = ""

        # At least three explanations are mandatory.
        # This implementation requires an explanation for
        # the first three questions and offers it for the rest.
        if index <= 3:
            while not explanation:
                explanation = input_func(
                    "Explain your answer in one or two sentences: "
                ).strip()

                if not explanation:
                    output_func("An explanation is required.")
        else:
            explanation = input_func(
                "Optional explanation (press Enter to skip): "
            ).strip()

        if explanation:
            explanations[f"Q{index}"] = explanation

    score = score_answers(answers)

    output_func(f"\nFinal score: {score}/10")

    output_func("\n===== ANSWER REVIEW =====")

    missed_topics = []

    for index, question in enumerate(QUESTIONS):
        given_answer = answers[index]
        correct_answer = question["answer"]

        output_func(f"\nQ{index + 1}: {question['topic']}")
        output_func(f"Your answer: {given_answer}")
        output_func(f"Correct answer: {correct_answer}")

        if given_answer == correct_answer:
            output_func("Result: Correct")
        else:
            output_func("Result: Review this topic")
            missed_topics.append(question["topic"])

        explanation = explanations.get(f"Q{index + 1}")

        if explanation:
            output_func(f"Your explanation: {explanation}")

    output_func("\n===== TOPICS TO REVISE =====")

    if missed_topics:
        for topic in missed_topics:
            output_func(f"- {topic}")
    else:
        output_func("No incorrect answers. Review your reasoning anyway.")

    session = {
        "participant": participant,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "choices": answers,
        "score": score,
        "explanations": explanations,
        "missed_topics": missed_topics,
    }

    session_directory = Path(session_directory)
    session_directory.mkdir(parents=True, exist_ok=True)

    session_file = (
        session_directory
        / f"session_{participant}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    )

    with session_file.open("w", encoding="utf-8") as file:
        json.dump(session, file, indent=4)

    output_func(f"\nLearning session saved to: {session_file}")

    return session