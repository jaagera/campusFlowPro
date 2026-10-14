import unittest

from campusflow.knowledge_lab import (
    QUESTIONS,
    ask_valid_choice,
    score_answers,
)


class TestKnowledgeLab(unittest.TestCase):

    def test_question_bank_contains_ten_questions(self):
        self.assertEqual(len(QUESTIONS), 10)

    def test_correct_answers_score_ten(self):
        answers = [
            question["answer"]
            for question in QUESTIONS
        ]

        self.assertEqual(score_answers(answers), 10)

    def test_all_wrong_answers_score_zero(self):
        answers = [
            next(
                option
                for option in ("A", "B", "C", "D")
                if option != question["answer"]
            )
            for question in QUESTIONS
        ]

        self.assertEqual(score_answers(answers), 0)

    def test_partial_score(self):
        answers = [
            question["answer"]
            for question in QUESTIONS
        ]

        answers[0] = "A" if answers[0] != "A" else "B"

        self.assertEqual(score_answers(answers), 9)

    def test_invalid_choice_is_rejected_and_reprompted(self):
        supplied_answers = iter(["E", "", "B"])

        def fake_input(prompt):
            return next(supplied_answers)

        result = ask_valid_choice(fake_input)

        self.assertEqual(result, "B")


if __name__ == "__main__":
    unittest.main()