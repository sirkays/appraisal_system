"""
Models for the CBT (Computer-Based Testing) module.

Defines exams, questions, options, assignments, attempts, and answers.
"""

import json
import random
from django.db import models
from django.conf import settings
from django.utils import timezone


class CBTExam(models.Model):
    """
    An exam that HR Admin creates and assigns to staff.

    Contains meta-information: title, instructions, duration, pass mark,
    and whether question order should be randomised per attempt.
    """

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (ACTIVE, "Active"),
        (CLOSED, "Closed"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(
        blank=True,
        help_text="Exam instructions or introductory text shown before the exam starts.",
    )
    duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Time allowed to complete the exam in minutes.",
    )
    pass_mark = models.PositiveSmallIntegerField(
        default=50,
        help_text="Minimum percentage score required to pass.",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=DRAFT,
    )
    randomise_questions = models.BooleanField(
        default=True,
        help_text="If True, question order will be shuffled for each attempt.",
    )
    allow_multiple_attempts = models.BooleanField(
        default=False,
        help_text="If True, staff can retake the exam after completing it.",
    )
    show_answers_after = models.BooleanField(
        default=True,
        help_text="If True, staff can see the correct answers after completing the exam.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_exams",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "CBT Exam"
        verbose_name_plural = "CBT Exams"

    def __str__(self):
        return self.title

    @property
    def total_marks(self):
        """Sum of marks across all questions."""
        return self.questions.aggregate(total=models.Sum("marks"))["total"] or 0

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def is_active(self):
        return self.status == self.ACTIVE


class CBTQuestion(models.Model):
    """A single question within a CBT exam."""

    exam = models.ForeignKey(
        CBTExam,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField(help_text="The question text.")
    marks = models.PositiveSmallIntegerField(
        default=1,
        help_text="Marks awarded for a correct answer.",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "CBT Question"
        verbose_name_plural = "CBT Questions"

    def __str__(self):
        return f"Q{self.order}: {self.text[:80]}"

    @property
    def correct_option(self):
        """Return the correct CBTOption for this question, or None."""
        return self.options.filter(is_correct=True).first()


class CBTOption(models.Model):
    """A multiple-choice option for a CBT question."""

    question = models.ForeignKey(
        CBTQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "CBT Option"
        verbose_name_plural = "CBT Options"

    def __str__(self):
        return f"{'✓ ' if self.is_correct else ''}{self.text[:60]}"


class CBTAssignment(models.Model):
    """
    Links an exam to target staff.

    HR Admin can assign by individual staff members, by department,
    or to all staff (leaving both target fields empty = everyone).
    """

    exam = models.ForeignKey(
        CBTExam,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    target_staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_exams",
        help_text="Specific staff members assigned to this exam.",
    )
    target_departments = models.ManyToManyField(
        "departments.Department",
        blank=True,
        related_name="cbt_assignments",
        help_text="Departments whose staff are assigned to this exam.",
    )
    assign_to_all = models.BooleanField(
        default=False,
        help_text="If True, every active staff member is assigned this exam.",
    )
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional deadline by which the exam must be completed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "CBT Assignment"
        verbose_name_plural = "CBT Assignments"

    def __str__(self):
        return f"Assignment for: {self.exam.title}"

    def is_assigned_to(self, user):
        """Return True if ``user`` is covered by this assignment."""
        if self.assign_to_all:
            return True
        if self.target_staff.filter(pk=user.pk).exists():
            return True
        if user.department and self.target_departments.filter(pk=user.department.pk).exists():
            return True
        return False


class CBTAttempt(models.Model):
    """
    A single attempt by a staff member at a CBT exam.

    Stores start/end times, the ordered list of question IDs (for
    randomisation reproducibility), and the final score.
    """

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    TIMED_OUT = "TIMED_OUT"

    STATUS_CHOICES = [
        (NOT_STARTED, "Not Started"),
        (IN_PROGRESS, "In Progress"),
        (SUBMITTED, "Submitted"),
        (TIMED_OUT, "Timed Out"),
    ]

    exam = models.ForeignKey(
        CBTExam,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cbt_attempts",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=NOT_STARTED,
    )
    # JSON list of question IDs in the order they were presented
    question_order = models.TextField(
        default="[]",
        help_text="JSON-encoded list of CBTQuestion PKs in presentation order.",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Scores
    raw_score = models.PositiveIntegerField(
        default=0,
        help_text="Total marks earned.",
    )
    total_marks = models.PositiveIntegerField(
        default=0,
        help_text="Total marks possible.",
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    passed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "CBT Attempt"
        verbose_name_plural = "CBT Attempts"

    def __str__(self):
        return f"{self.staff.full_name} — {self.exam.title}"

    def get_question_order(self):
        """Return the question ID list."""
        return json.loads(self.question_order)

    def set_question_order(self, id_list):
        """Save the question ID list."""
        self.question_order = json.dumps(id_list)

    def get_ordered_questions(self):
        """Return CBTQuestion QuerySet in the stored presentation order."""
        id_list = self.get_question_order()
        questions = {q.pk: q for q in self.exam.questions.prefetch_related("options").all()}
        return [questions[pk] for pk in id_list if pk in questions]

    @property
    def time_limit_seconds(self):
        return self.exam.duration_minutes * 60

    @property
    def seconds_elapsed(self):
        if self.started_at:
            return int((timezone.now() - self.started_at).total_seconds())
        return 0

    @property
    def seconds_remaining(self):
        remaining = self.time_limit_seconds - self.seconds_elapsed
        return max(remaining, 0)

    @property
    def is_timed_out(self):
        return self.seconds_remaining == 0 and self.status == self.IN_PROGRESS

    def initialise(self):
        """Set up a fresh attempt: build question order and start timer."""
        questions = list(self.exam.questions.values_list("pk", flat=True))
        if self.exam.randomise_questions:
            random.shuffle(questions)
        self.set_question_order(questions)
        self.started_at = timezone.now()
        self.status = self.IN_PROGRESS
        self.total_marks = self.exam.total_marks

    def calculate_score(self):
        """Compute raw_score, percentage, and passed from submitted answers."""
        correct_answers = 0
        for answer in self.answers.select_related("selected_option").all():
            if answer.selected_option and answer.selected_option.is_correct:
                correct_answers += answer.question.marks
        self.raw_score = correct_answers
        total = self.total_marks or 1
        self.percentage = round((self.raw_score / total) * 100, 2)
        self.passed = self.percentage >= self.exam.pass_mark


class CBTAnswer(models.Model):
    """The answer a staff member selected for a question during an attempt."""

    attempt = models.ForeignKey(
        CBTAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        CBTQuestion,
        on_delete=models.CASCADE,
    )
    selected_option = models.ForeignKey(
        CBTOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = [("attempt", "question")]
        verbose_name = "CBT Answer"
        verbose_name_plural = "CBT Answers"

    def __str__(self):
        return f"Attempt {self.attempt.pk} — Q{self.question.pk}"

    @property
    def is_correct(self):
        return self.selected_option is not None and self.selected_option.is_correct
