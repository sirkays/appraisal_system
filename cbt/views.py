"""
Views for the CBT (Computer-Based Testing) module.

Staff views  : exam_list, exam_detail, start_exam, take_exam, submit_exam,
               exam_result, my_results
HR Admin views: hr_exam_list, hr_exam_create, hr_exam_edit, hr_exam_delete,
               hr_question_manager, hr_question_delete, hr_option_delete,
               hr_exam_assign, hr_exam_results
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.db.models import Q

from .models import (
    CBTExam, CBTQuestion, CBTOption,
    CBTAssignment, CBTAttempt, CBTAnswer,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hr_required(view_func):
    """Decorator: restrict view to HR_ADMIN role."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != "HR_ADMIN":
            messages.error(request, "You do not have permission to access that page.")
            return redirect("cbt:exam_list")
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_assigned_exam_ids(user):
    """Return a set of exam PKs the user is assigned to."""
    assigned_ids = set()
    for assignment in CBTAssignment.objects.prefetch_related(
        "target_staff", "target_departments"
    ).filter(exam__status=CBTExam.ACTIVE):
        if assignment.is_assigned_to(user):
            assigned_ids.add(assignment.exam_id)
    return assigned_ids


# ─────────────────────────────────────────────────────────────────────────────
# Staff Views
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def exam_list(request):
    """Display all active exams assigned to the logged-in user."""
    assigned_ids = _get_assigned_exam_ids(request.user)
    exams = CBTExam.objects.filter(pk__in=assigned_ids, status=CBTExam.ACTIVE)

    # Attach attempt info to each exam
    user_attempts = {
        a.exam_id: a
        for a in CBTAttempt.objects.filter(
            staff=request.user, exam_id__in=assigned_ids
        ).order_by("-created_at")
    }

    # Annotate each exam with deadline (from assignment) and attempt
    exam_data = []
    for exam in exams:
        assignment = CBTAssignment.objects.filter(exam=exam).first()
        attempt = user_attempts.get(exam.pk)
        can_start = (
            attempt is None
            or (exam.allow_multiple_attempts and attempt.status in (CBTAttempt.SUBMITTED, CBTAttempt.TIMED_OUT))
        )
        exam_data.append({
            "exam": exam,
            "attempt": attempt,
            "can_start": can_start,
            "deadline": assignment.deadline if assignment else None,
        })

    return render(request, "cbt/exam_list.html", {"exam_data": exam_data})


@login_required
def exam_detail(request, pk):
    """Show exam information and a 'Start' button."""
    exam = get_object_or_404(CBTExam, pk=pk, status=CBTExam.ACTIVE)
    assigned_ids = _get_assigned_exam_ids(request.user)
    if exam.pk not in assigned_ids:
        messages.error(request, "You are not assigned to this exam.")
        return redirect("cbt:exam_list")

    existing_attempt = CBTAttempt.objects.filter(
        staff=request.user, exam=exam
    ).order_by("-created_at").first()

    can_start = (
        existing_attempt is None
        or (
            exam.allow_multiple_attempts
            and existing_attempt.status in (CBTAttempt.SUBMITTED, CBTAttempt.TIMED_OUT)
        )
    )

    # Resume in-progress attempt
    if existing_attempt and existing_attempt.status == CBTAttempt.IN_PROGRESS:
        if not existing_attempt.is_timed_out:
            return redirect("cbt:take_exam", pk=existing_attempt.pk)
        else:
            # Auto-close timed-out attempt
            existing_attempt.status = CBTAttempt.TIMED_OUT
            existing_attempt.submitted_at = timezone.now()
            existing_attempt.calculate_score()
            existing_attempt.save()
            return redirect("cbt:exam_result", pk=existing_attempt.pk)

    assignment = CBTAssignment.objects.filter(exam=exam).first()

    return render(request, "cbt/exam_detail.html", {
        "exam": exam,
        "existing_attempt": existing_attempt,
        "can_start": can_start,
        "deadline": assignment.deadline if assignment else None,
    })


@login_required
def start_exam(request, pk):
    """POST: Create a new CBTAttempt and redirect to the exam room."""
    if request.method != "POST":
        return redirect("cbt:exam_detail", pk=pk)

    exam = get_object_or_404(CBTExam, pk=pk, status=CBTExam.ACTIVE)
    assigned_ids = _get_assigned_exam_ids(request.user)
    if exam.pk not in assigned_ids:
        messages.error(request, "You are not assigned to this exam.")
        return redirect("cbt:exam_list")

    if exam.question_count == 0:
        messages.error(request, "This exam has no questions yet.")
        return redirect("cbt:exam_detail", pk=pk)

    existing = CBTAttempt.objects.filter(staff=request.user, exam=exam).order_by("-created_at").first()

    if existing:
        if existing.status == CBTAttempt.IN_PROGRESS and not existing.is_timed_out:
            return redirect("cbt:take_exam", pk=existing.pk)
        if not exam.allow_multiple_attempts and existing.status in (CBTAttempt.SUBMITTED, CBTAttempt.TIMED_OUT):
            messages.error(request, "You have already completed this exam.")
            return redirect("cbt:exam_result", pk=existing.pk)

    attempt = CBTAttempt(exam=exam, staff=request.user)
    attempt.initialise()
    attempt.save()
    return redirect("cbt:take_exam", pk=attempt.pk)


@login_required
def take_exam(request, pk):
    """Display the timed exam interface."""
    attempt = get_object_or_404(CBTAttempt, pk=pk, staff=request.user)

    # Guard: only IN_PROGRESS attempts are accessible here
    if attempt.status not in (CBTAttempt.NOT_STARTED, CBTAttempt.IN_PROGRESS):
        return redirect("cbt:exam_result", pk=pk)

    # Auto-timeout check
    if attempt.is_timed_out:
        attempt.status = CBTAttempt.TIMED_OUT
        attempt.submitted_at = timezone.now()
        attempt.calculate_score()
        attempt.save()
        messages.warning(request, "Time expired — your exam has been automatically submitted.")
        return redirect("cbt:exam_result", pk=pk)

    questions = attempt.get_ordered_questions()

    # Build existing answers map {question_id: option_id}
    existing_answers = {
        a.question_id: a.selected_option_id
        for a in attempt.answers.all()
    }

    return render(request, "cbt/take_exam.html", {
        "attempt": attempt,
        "questions": questions,
        "existing_answers": existing_answers,
        "seconds_remaining": attempt.seconds_remaining,
    })


@login_required
def submit_exam(request, pk):
    """POST: Save answers and calculate score."""
    attempt = get_object_or_404(CBTAttempt, pk=pk, staff=request.user)

    if attempt.status not in (CBTAttempt.IN_PROGRESS, CBTAttempt.NOT_STARTED):
        return redirect("cbt:exam_result", pk=pk)

    if request.method == "POST":
        questions = attempt.get_ordered_questions()

        for question in questions:
            field_name = f"question_{question.pk}"
            option_id = request.POST.get(field_name)

            answer, _ = CBTAnswer.objects.get_or_create(
                attempt=attempt,
                question=question,
            )
            if option_id:
                try:
                    option = CBTOption.objects.get(pk=option_id, question=question)
                    answer.selected_option = option
                except CBTOption.DoesNotExist:
                    answer.selected_option = None
            else:
                answer.selected_option = None
            answer.save()

        # Determine status: timed out or submitted
        if attempt.is_timed_out:
            attempt.status = CBTAttempt.TIMED_OUT
        else:
            attempt.status = CBTAttempt.SUBMITTED

        attempt.submitted_at = timezone.now()
        attempt.calculate_score()
        attempt.save()

        messages.success(request, "Your exam has been submitted successfully.")
        return redirect("cbt:exam_result", pk=attempt.pk)

    return redirect("cbt:take_exam", pk=pk)


@login_required
def exam_result(request, pk):
    """Display the result of a completed attempt."""
    attempt = get_object_or_404(CBTAttempt, pk=pk, staff=request.user)

    if attempt.status == CBTAttempt.IN_PROGRESS:
        return redirect("cbt:take_exam", pk=pk)

    # Build per-question result data
    answers = {a.question_id: a for a in attempt.answers.select_related("selected_option").all()}
    questions = attempt.get_ordered_questions()
    question_results = []
    for q in questions:
        answer = answers.get(q.pk)
        question_results.append({
            "question": q,
            "selected_option": answer.selected_option if answer else None,
            "is_correct": answer.is_correct if answer else False,
            "correct_option": q.correct_option,
        })

    return render(request, "cbt/exam_result.html", {
        "attempt": attempt,
        "question_results": question_results,
        "show_answers": attempt.exam.show_answers_after,
    })


@login_required
def my_results(request):
    """Show all past CBT attempts for the logged-in user."""
    attempts = CBTAttempt.objects.filter(
        staff=request.user
    ).exclude(
        status=CBTAttempt.IN_PROGRESS
    ).select_related("exam").order_by("-submitted_at")

    return render(request, "cbt/my_results.html", {"attempts": attempts})


# ─────────────────────────────────────────────────────────────────────────────
# HR Admin Views
# ─────────────────────────────────────────────────────────────────────────────

@_hr_required
def hr_exam_list(request):
    """HR Admin: list all exams."""
    exams = CBTExam.objects.select_related("created_by").all()
    return render(request, "cbt/hr/exam_list.html", {"exams": exams})


@_hr_required
def hr_exam_create(request):
    """HR Admin: create a new exam."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        duration = request.POST.get("duration_minutes", 30)
        pass_mark = request.POST.get("pass_mark", 50)
        status = request.POST.get("status", CBTExam.DRAFT)
        randomise = request.POST.get("randomise_questions") == "on"
        allow_multiple = request.POST.get("allow_multiple_attempts") == "on"
        show_answers = request.POST.get("show_answers_after") == "on"

        if not title:
            messages.error(request, "Exam title is required.")
        else:
            exam = CBTExam.objects.create(
                title=title,
                description=description,
                duration_minutes=int(duration),
                pass_mark=int(pass_mark),
                status=status,
                randomise_questions=randomise,
                allow_multiple_attempts=allow_multiple,
                show_answers_after=show_answers,
                created_by=request.user,
            )
            messages.success(request, f'Exam "{exam.title}" created. Now add questions.')
            return redirect("cbt:hr_question_manager", pk=exam.pk)

    return render(request, "cbt/hr/exam_form.html", {"form_title": "Create New Exam", "exam": None})


@_hr_required
def hr_exam_edit(request, pk):
    """HR Admin: edit an existing exam."""
    exam = get_object_or_404(CBTExam, pk=pk)

    if request.method == "POST":
        exam.title = request.POST.get("title", exam.title).strip()
        exam.description = request.POST.get("description", "").strip()
        exam.duration_minutes = int(request.POST.get("duration_minutes", exam.duration_minutes))
        exam.pass_mark = int(request.POST.get("pass_mark", exam.pass_mark))
        exam.status = request.POST.get("status", exam.status)
        exam.randomise_questions = request.POST.get("randomise_questions") == "on"
        exam.allow_multiple_attempts = request.POST.get("allow_multiple_attempts") == "on"
        exam.show_answers_after = request.POST.get("show_answers_after") == "on"
        exam.save()
        messages.success(request, f'Exam "{exam.title}" updated successfully.')
        return redirect("cbt:hr_exam_list")

    return render(request, "cbt/hr/exam_form.html", {"form_title": "Edit Exam", "exam": exam})


@_hr_required
def hr_exam_delete(request, pk):
    """HR Admin: delete an exam (POST only)."""
    exam = get_object_or_404(CBTExam, pk=pk)
    if request.method == "POST":
        title = exam.title
        exam.delete()
        messages.success(request, f'Exam "{title}" has been deleted.')
    return redirect("cbt:hr_exam_list")


@_hr_required
def hr_question_manager(request, pk):
    """HR Admin: add/edit questions and options for an exam."""
    exam = get_object_or_404(CBTExam, pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_question":
            text = request.POST.get("text", "").strip()
            marks = int(request.POST.get("marks", 1))
            order = exam.questions.count() + 1
            if text:
                q = CBTQuestion.objects.create(exam=exam, text=text, marks=marks, order=order)
                # Save options
                for i in range(1, 6):
                    opt_text = request.POST.get(f"option_{i}", "").strip()
                    is_correct = request.POST.get("correct_option") == str(i)
                    if opt_text:
                        CBTOption.objects.create(
                            question=q,
                            text=opt_text,
                            is_correct=is_correct,
                            order=i,
                        )
                messages.success(request, "Question added successfully.")
            else:
                messages.error(request, "Question text cannot be empty.")

        elif action == "edit_question":
            qpk = request.POST.get("question_id")
            question = get_object_or_404(CBTQuestion, pk=qpk, exam=exam)
            question.text = request.POST.get("text", question.text).strip()
            question.marks = int(request.POST.get("marks", question.marks))
            question.save()

            # Update existing options and add new ones
            correct_index = request.POST.get("correct_option")
            existing_options = list(question.options.order_by("order"))
            for idx, opt in enumerate(existing_options, start=1):
                opt_text = request.POST.get(f"option_{idx}", "").strip()
                if opt_text:
                    opt.text = opt_text
                    opt.is_correct = (correct_index == str(idx))
                    opt.save()

            # Handle new options beyond existing count
            for i in range(len(existing_options) + 1, 6):
                opt_text = request.POST.get(f"option_{i}", "").strip()
                if opt_text:
                    CBTOption.objects.create(
                        question=question,
                        text=opt_text,
                        is_correct=(correct_index == str(i)),
                        order=i,
                    )
            messages.success(request, "Question updated.")

        return redirect("cbt:hr_question_manager", pk=pk)

    questions = exam.questions.prefetch_related("options").all()
    return render(request, "cbt/hr/question_manager.html", {
        "exam": exam,
        "questions": questions,
    })


@_hr_required
def hr_question_delete(request, pk, qpk):
    """HR Admin: delete a question (POST)."""
    exam = get_object_or_404(CBTExam, pk=pk)
    question = get_object_or_404(CBTQuestion, pk=qpk, exam=exam)
    if request.method == "POST":
        question.delete()
        messages.success(request, "Question deleted.")
    return redirect("cbt:hr_question_manager", pk=pk)


@_hr_required
def hr_option_delete(request, pk, opk):
    """HR Admin: delete an option (POST)."""
    exam = get_object_or_404(CBTExam, pk=pk)
    option = get_object_or_404(CBTOption, pk=opk, question__exam=exam)
    if request.method == "POST":
        option.delete()
        messages.success(request, "Option deleted.")
    return redirect("cbt:hr_question_manager", pk=pk)


@_hr_required
def hr_exam_assign(request, pk):
    """HR Admin: assign an exam to staff/departments."""
    from accounts.models import CustomUser
    from departments.models import Department

    exam = get_object_or_404(CBTExam, pk=pk)
    assignment, _ = CBTAssignment.objects.get_or_create(exam=exam)

    if request.method == "POST":
        assign_to_all = request.POST.get("assign_to_all") == "on"
        assignment.assign_to_all = assign_to_all

        deadline_str = request.POST.get("deadline", "").strip()
        if deadline_str:
            from django.utils.dateparse import parse_datetime
            deadline = parse_datetime(deadline_str)
            assignment.deadline = deadline
        else:
            assignment.deadline = None

        assignment.save()

        if not assign_to_all:
            staff_ids = request.POST.getlist("target_staff")
            dept_ids = request.POST.getlist("target_departments")
            assignment.target_staff.set(staff_ids)
            assignment.target_departments.set(dept_ids)
        else:
            assignment.target_staff.clear()
            assignment.target_departments.clear()

        messages.success(request, "Assignment updated successfully.")
        return redirect("cbt:hr_exam_list")

    all_staff = CustomUser.objects.filter(is_active=True).exclude(role="HR_ADMIN")
    all_departments = Department.objects.all()

    return render(request, "cbt/hr/exam_assign.html", {
        "exam": exam,
        "assignment": assignment,
        "all_staff": all_staff,
        "all_departments": all_departments,
        "selected_staff": list(assignment.target_staff.values_list("pk", flat=True)),
        "selected_departments": list(assignment.target_departments.values_list("pk", flat=True)),
    })


@_hr_required
def hr_exam_results(request, pk):
    """HR Admin: view all attempt results for an exam."""
    exam = get_object_or_404(CBTExam, pk=pk)
    attempts = CBTAttempt.objects.filter(
        exam=exam
    ).exclude(
        status=CBTAttempt.IN_PROGRESS
    ).select_related("staff", "staff__department").order_by("-submitted_at")

    total_attempts = attempts.count()
    passed = attempts.filter(passed=True).count()
    failed = total_attempts - passed

    return render(request, "cbt/hr/exam_results.html", {
        "exam": exam,
        "attempts": attempts,
        "total_attempts": total_attempts,
        "passed": passed,
        "failed": failed,
    })
