from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from .models import CBTAnswer, CBTAttempt, CBTExam, CBTOption, CBTQuestion


class CBTAutosaveTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="cbt_staff",
            password="pass12345",
            staff_id="CBT-001",
            role=CustomUser.STAFF,
        )
        self.other_staff = CustomUser.objects.create_user(
            username="other_cbt_staff",
            password="pass12345",
            staff_id="CBT-002",
            role=CustomUser.STAFF,
        )
        self.exam = CBTExam.objects.create(
            title="Autosave Exam",
            duration_minutes=30,
            status=CBTExam.ACTIVE,
            randomise_questions=False,
            created_by=self.staff,
        )
        self.question = CBTQuestion.objects.create(
            exam=self.exam,
            text="What should happen after reload?",
            order=1,
        )
        self.option_a = CBTOption.objects.create(
            question=self.question,
            text="Saved answer remains selected",
            is_correct=True,
            order=1,
        )
        self.option_b = CBTOption.objects.create(
            question=self.question,
            text="Answer is lost",
            is_correct=False,
            order=2,
        )
        self.attempt = CBTAttempt(exam=self.exam, staff=self.staff)
        self.attempt.initialise()
        self.attempt.save()

    def test_save_answer_persists_selected_option(self):
        self.client.login(username="cbt_staff", password="pass12345")

        response = self.client.post(
            reverse("cbt:save_answer", args=[self.attempt.id]),
            {"question_id": str(self.question.id), "option_id": str(self.option_a.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        answer = CBTAnswer.objects.get(attempt=self.attempt, question=self.question)
        self.assertEqual(answer.selected_option, self.option_a)

    def test_take_exam_restores_autosaved_answer_after_reload(self):
        CBTAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            selected_option=self.option_a,
        )
        self.client.login(username="cbt_staff", password="pass12345")

        response = self.client.get(reverse("cbt:take_exam", args=[self.attempt.id]))

        self.assertContains(response, f'id="q{self.question.id}_opt{self.option_a.id}"')
        self.assertContains(response, "checked")

    def test_other_user_cannot_autosave_attempt_answer(self):
        self.client.login(username="other_cbt_staff", password="pass12345")

        response = self.client.post(
            reverse("cbt:save_answer", args=[self.attempt.id]),
            {"question_id": str(self.question.id), "option_id": str(self.option_a.id)},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(CBTAnswer.objects.filter(attempt=self.attempt).exists())
