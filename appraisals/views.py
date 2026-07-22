"""
Views for the Performance Appraisals app.

Implements the fully dynamic multi-step approval workflow:
  Staff self-assessment → Step 1 Approver → Step 2 Approver → ... → Approved → Staff Acknowledgement

The approval chain is configured via ApprovalProcess/ApprovalStep models per cycle.
Each appraisal uses either the cycle's general process or a per-staff override process.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from accounts.models import CustomUser
from .models import (
    AppraisalCycle, Appraisal, KPICategory, KPIItem,
    KPIScore, CompetencyCategory, CompetencyItem, CompetencyScore,
    NarrativeField, NarrativeResponse, ApprovalStep, AppraisalApprovalAssignment,
    SupervisorReview, FormSection, FormField, FormFieldResponse,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _user_can_view_appraisal(request, appraisal):
    """Return whether the current user may view/download this appraisal."""
    return (
        appraisal.staff == request.user or
        request.user.role == CustomUser.HR_ADMIN or
        appraisal.approval_assignments.filter(approver=request.user).exists()
    )


def _build_appraisal_result_context(request, appraisal):
    """Build shared context for on-screen and downloadable appraisal results."""
    is_own = appraisal.staff == request.user

    all_assignments = appraisal.approval_assignments.select_related(
        'step', 'approver'
    ).order_by('step__step_number')

    can_acknowledge = (
        is_own and
        appraisal.status == Appraisal.APPROVED and
        not appraisal.staff_acknowledged_at
    )

    # Build sections for display — all configured fields with all responses.
    # Empty sections are skipped so blank instruction-only cards are not shown.
    result_sections = []
    for section in FormSection.objects.filter(cycle=appraisal.cycle).order_by('order'):
        fields_data = []
        for field in section.fields.order_by('order'):
            primary_resp = FormFieldResponse.objects.filter(
                appraisal=appraisal,
                field=field,
                response_type=FormFieldResponse.PRIMARY,
            ).select_related('responded_by').first()

            mode_b_responses = FormFieldResponse.objects.filter(
                appraisal=appraisal,
                field=field,
                response_type__in=[FormFieldResponse.REVIEWER_SCORE, FormFieldResponse.REVIEWER_COMMENT],
            ).select_related('responded_by')

            fields_data.append({
                'field': field,
                'response': primary_resp,
                'mode_b_responses': mode_b_responses,
            })
        if fields_data:
            result_sections.append({'section': section, 'fields': fields_data})

    return {
        'appraisal': appraisal,
        'all_assignments': all_assignments,
        'can_acknowledge': can_acknowledge,
        'is_own': is_own,
        'result_sections': result_sections,
        'FIELD_TYPE': {
            'NARRATIVE': FormField.NARRATIVE,
            'SCORE': FormField.SCORE,
            'SCORE_COMMENT': FormField.SCORE_COMMENT,
            'SINGLE_SELECT': FormField.SINGLE_SELECT,
            'MULTI_SELECT': FormField.MULTI_SELECT,
        },
        'RESPONSE_TYPE': {
            'REVIEWER_SCORE': FormFieldResponse.REVIEWER_SCORE,
            'REVIEWER_COMMENT': FormFieldResponse.REVIEWER_COMMENT,
        },
    }


def _appraisal_recency_timestamp(appraisal):
    """Best timestamp for ordering appraisals by recent activity/submission."""
    if not appraisal:
        return datetime.min.replace(tzinfo=dt_timezone.utc)
    return appraisal.self_submitted_at or appraisal.updated_at or appraisal.created_at


def _team_appraisal_sort_key(item):
    """Sort reviewer team rows with recent actionable submissions first."""
    appraisal = item.get('appraisal')
    if not appraisal:
        return (4, 0, item['member'].get_full_name().lower())

    if appraisal.status in [Appraisal.SUBMITTED, Appraisal.AWAITING_STEP_REVIEW, Appraisal.RETURNED_TO_REVIEWER]:
        priority = 0
    elif appraisal.status in [Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED, Appraisal.ARCHIVED]:
        priority = 1
    elif appraisal.status == Appraisal.RETURNED_TO_STAFF:
        priority = 2
    else:
        priority = 3

    return (priority, -_appraisal_recency_timestamp(appraisal).timestamp(), item['member'].get_full_name().lower())

def _calculate_weighted_score(appraisal, score_type='self'):
    """
    Calculate the overall weighted score for an appraisal using FormSection weights.

    score_type:
      'self'       → uses FormFieldResponse where responded_by == appraisal.staff (PRIMARY)
      'supervisor' → uses FormFieldResponse where response_type == PRIMARY and
                     filled_by != APPRAISEE (reviewer responses)

    Returns a Decimal score or None if no scored fields exist.
    """
    total_weight = Decimal('0.00')
    total_weighted_score = Decimal('0.00')

    for section in FormSection.objects.filter(cycle=appraisal.cycle):
        weight = section.section_weight
        if not weight:
            continue  # Narrative-only sections don't contribute

        scored_fields = section.fields.filter(
            field_type__in=[FormField.SCORE, FormField.SCORE_COMMENT]
        )
        if not scored_fields.exists():
            continue

        if score_type == 'self':
            responses = FormFieldResponse.objects.filter(
                appraisal=appraisal,
                field__in=scored_fields,
                responded_by=appraisal.staff,
                response_type=FormFieldResponse.PRIMARY,
                score__isnull=False,
            )
        else:
            responses = FormFieldResponse.objects.filter(
                appraisal=appraisal,
                field__in=scored_fields,
                response_type=FormFieldResponse.PRIMARY,
                score__isnull=False,
            ).exclude(responded_by=appraisal.staff)

        if not responses.exists():
            continue

        # Sum of (score / max_score) * max_score contribution per section
        section_total = Decimal('0.00')
        section_max = Decimal('0.00')
        for resp in responses:
            section_total += resp.score or Decimal('0')
            section_max += resp.field.max_score

        if section_max > 0:
            # Normalize to weight: (obtained / max) * weight
            section_score = (section_total / section_max) * weight
            total_weighted_score += section_score
            total_weight += weight

    if total_weight == 0:
        return None
    return total_weighted_score.quantize(Decimal('0.01'))


def _send_notification(recipient, sender, notification_type, title, message, appraisal=None):
    """Helper to create a notification safely."""
    if not recipient:
        return
    try:
        from notifications.models import Notification
        Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            related_appraisal=appraisal,
        )
    except Exception:
        pass


def _advance_appraisal(appraisal, current_assignment, actioning_user):
    """
    Mark the current step as APPROVED and advance to the next step.
    If no next step exists, mark the appraisal as fully APPROVED.
    """
    from notifications.models import Notification

    current_assignment.status = AppraisalApprovalAssignment.APPROVED
    current_assignment.actioned_at = timezone.now()
    current_assignment.save()

    process = appraisal.active_process
    if not process:
        appraisal.status = Appraisal.APPROVED
        appraisal.final_score = appraisal.overall_supervisor_score
        appraisal.save()
        _send_notification(
            appraisal.staff, actioning_user,
            Notification.APPRAISAL_APPROVED,
            "Appraisal Approved",
            f"Your appraisal for {appraisal.cycle.name} has been approved.",
            appraisal
        )
        return

    next_step_number = appraisal.current_step_number + 1
    next_step = process.steps.filter(step_number=next_step_number).first()

    if next_step:
        appraisal.current_step_number = next_step_number
        appraisal.status = Appraisal.AWAITING_STEP_REVIEW
        appraisal.save()

        # Notify the next step's assigned approver
        next_assignment = appraisal.approval_assignments.filter(step=next_step).first()
        if next_assignment and next_assignment.approver:
            next_assignment.status = AppraisalApprovalAssignment.PENDING
            next_assignment.actioned_at = None
            next_assignment.save(update_fields=['status', 'actioned_at'])

            _send_notification(
                next_assignment.approver, actioning_user,
                Notification.APPRAISAL_REVIEWED,
                f"Appraisal Awaiting Your Review — Step {next_step_number}",
                f"{appraisal.staff.get_full_name()}'s appraisal is now awaiting your action at step {next_step_number}: {next_step.label}.",
                appraisal
            )
    else:
        # All steps complete
        appraisal.status = Appraisal.APPROVED
        appraisal.final_score = appraisal.overall_supervisor_score or appraisal.overall_self_score
        appraisal.save()

        _send_notification(
            appraisal.staff, actioning_user,
            Notification.APPRAISAL_APPROVED,
            "Your Appraisal Has Been Fully Approved",
            f"Your appraisal for {appraisal.cycle.name} has been fully approved. Please log in to view your final result and acknowledge.",
            appraisal
        )


def _return_appraisal(appraisal, current_assignment, actioning_user, return_comment):
    """
    Return the appraisal. Step 1 returns go to staff; higher steps return to previous step.
    Keep the latest return reason on the appraisal and the assignment so
    every reviewer page can display why the appraisal was returned.
    Also writes an immutable ReturnLog entry so the full history is always preserved.
    """
    from notifications.models import Notification
    from appraisals.models import AppraisalReturnLog

    current_step_number = appraisal.current_step_number
    current_assignment.status = AppraisalApprovalAssignment.RETURNED
    current_assignment.comments = return_comment
    current_assignment.actioned_at = timezone.now()
    current_assignment.save()

    if current_step_number <= 1:
        to_step = 0  # back to staff
        # Return to staff
        appraisal.status = Appraisal.RETURNED_TO_STAFF
        appraisal.supervisor_return_notes = return_comment
        appraisal.current_step_number = 0
        appraisal.save()

        _send_notification(
            appraisal.staff, actioning_user,
            Notification.APPRAISAL_RETURNED,
            "Your Appraisal Has Been Returned for Revision",
            f"Your appraisal has been returned by the reviewer. Reason: {return_comment}" if return_comment
            else "Your appraisal has been returned for revision.",
            appraisal
        )
    else:
        # Return to previous step
        prev_step_number = current_step_number - 1
        to_step = prev_step_number
        process = appraisal.active_process
        prev_step = process.steps.filter(step_number=prev_step_number).first() if process else None

        appraisal.status = Appraisal.RETURNED_TO_REVIEWER
        appraisal.hod_return_notes = return_comment
        appraisal.current_step_number = prev_step_number
        appraisal.save()

        if prev_step:
            # Reset the previous step's assignment back to PENDING
            prev_assignment = appraisal.approval_assignments.filter(step=prev_step).first()
            if prev_assignment:
                prev_assignment.status = AppraisalApprovalAssignment.PENDING
                prev_assignment.save()

                _send_notification(
                    prev_assignment.approver, actioning_user,
                    Notification.APPRAISAL_RETURNED,
                    f"Appraisal Returned to Step {prev_step_number}",
                    f"{appraisal.staff.get_full_name()}'s appraisal was returned by {actioning_user.get_full_name()} at step {current_step_number}. Reason: {return_comment}",
                    appraisal
                )

    # Write immutable return log entry
    AppraisalReturnLog.objects.create(
        appraisal=appraisal,
        reviewer=actioning_user,
        step=current_assignment.step,
        from_step_number=current_step_number,
        to_step_number=to_step,
        reason=return_comment or '',
    )

    # NOTE: Do NOT reset the current (returning) assignment — it stays RETURNED.
    # The previous step assignment was already reset to PENDING above.


# ============================================================
# STAFF SELF-APPRAISAL
# ============================================================

@login_required
def self_appraisal_form(request, pk=None):
    """
    Dynamic self-appraisal form for staff.

    Renders all FormSection/FormField records where filled_by=APPRAISEE for
    the active cycle. Saves responses to FormFieldResponse.
    Supports NARRATIVE, SCORE, SCORE_COMMENT, SINGLE_SELECT, MULTI_SELECT field types.
    """
    from accounts.views import _get_selected_cycle

    if pk:
        appraisal = get_object_or_404(Appraisal, pk=pk, staff=request.user)
        active_cycle = appraisal.cycle
    else:
        active_cycle = _get_selected_cycle(request)
        if not active_cycle:
            messages.warning(request, "There is currently no active appraisal cycle.")
            return redirect('accounts:dashboard_redirect')

        appraisal, created = Appraisal.objects.get_or_create(
            cycle=active_cycle,
            staff=request.user,
            defaults={
                'status': Appraisal.DRAFT,
                'supervisor': request.user.supervisor,
            }
        )

    is_editable = appraisal.status in [Appraisal.NOT_STARTED, Appraisal.DRAFT, Appraisal.RETURNED_TO_STAFF]

    if appraisal.status == Appraisal.NOT_STARTED:
        appraisal.status = Appraisal.DRAFT
        appraisal.save()

    # Fetch all APPRAISEE-filled fields from the form sections
    appraisee_sections = (
        FormSection.objects
        .filter(cycle=active_cycle)
        .prefetch_related('fields')
        .order_by('order')
    )

    # Pre-create empty FormFieldResponse records so staff can see all fields
    for section in appraisee_sections:
        for field in section.fields.filter(filled_by=FormField.APPRAISEE).order_by('order'):
            FormFieldResponse.objects.get_or_create(
                appraisal=appraisal,
                field=field,
                responded_by=request.user,
                response_type=FormFieldResponse.PRIMARY,
            )

    if request.method == 'POST':
        if not is_editable:
            messages.error(request, "This appraisal is already submitted and cannot be modified.")
            return redirect('appraisals:self_appraisal_form')

        action = request.POST.get('action', 'save_draft')

        # --- Save all appraisee field responses ---
        appraisee_responses = FormFieldResponse.objects.filter(
            appraisal=appraisal,
            responded_by=request.user,
            response_type=FormFieldResponse.PRIMARY,
            field__filled_by=FormField.APPRAISEE,
        ).select_related('field')

        missing_fields = []

        for resp in appraisee_responses:
            field = resp.field
            ftype = field.field_type
            post_key = f'field_{resp.field_id}'

            if ftype == FormField.NARRATIVE:
                resp.text_response = request.POST.get(post_key, '').strip()

            elif ftype == FormField.SCORE:
                val = request.POST.get(post_key, '').strip()
                try:
                    resp.score = Decimal(val) if val else None
                except InvalidOperation:
                    resp.score = None

            elif ftype == FormField.SCORE_COMMENT:
                val = request.POST.get(f'{post_key}_score', '').strip()
                try:
                    resp.score = Decimal(val) if val else None
                except InvalidOperation:
                    resp.score = None
                resp.text_response = request.POST.get(f'{post_key}_comment', '').strip()

            elif ftype == FormField.SINGLE_SELECT:
                selected = request.POST.get(post_key, '')
                resp.selected_options = [selected] if selected else []

            elif ftype == FormField.MULTI_SELECT:
                selected = request.POST.getlist(post_key)
                resp.selected_options = selected

            # Evidence file
            evidence = request.FILES.get(f'{post_key}_evidence')
            if evidence:
                resp.evidence_file = evidence

            resp.save()

            # Validate required fields on submit
            if action == 'submit' and field.is_required:
                if ftype == FormField.NARRATIVE and not resp.text_response:
                    missing_fields.append(field.label)
                elif ftype in (FormField.SCORE, FormField.SCORE_COMMENT) and resp.score is None:
                    missing_fields.append(field.label)
                elif ftype in (FormField.SINGLE_SELECT, FormField.MULTI_SELECT) and not resp.selected_options:
                    missing_fields.append(field.label)

        if action == 'submit':
            if missing_fields:
                messages.error(
                    request,
                    f"Cannot submit. Missing required fields: {', '.join(missing_fields[:5])}"
                    + (f" and {len(missing_fields)-5} more..." if len(missing_fields) > 5 else "")
                )
                return redirect('appraisals:self_appraisal_form')

            # Calculate overall self-score from FormFieldResponse
            appraisal.overall_self_score = _calculate_weighted_score(appraisal, 'self')

            # Determine the first step of the active process
            process = appraisal.active_process
            if process:
                first_step = process.steps.first()
                if first_step:
                    appraisal.current_step_number = first_step.step_number
                    appraisal.status = Appraisal.SUBMITTED

                    # Initialize assignment records if not yet created
                    from hr_admin.views import _create_assignments_for_appraisal
                    _create_assignments_for_appraisal(appraisal, process)

                    # Notify the first step's approver
                    first_assignment = appraisal.approval_assignments.filter(
                        step__step_number=first_step.step_number
                    ).first()
                    if first_assignment:
                        first_assignment.status = AppraisalApprovalAssignment.PENDING
                        first_assignment.actioned_at = None
                        first_assignment.save(update_fields=['status', 'actioned_at'])

                    if first_assignment and first_assignment.approver:
                        from notifications.models import Notification
                        _send_notification(
                            first_assignment.approver, request.user,
                            Notification.APPRAISAL_SUBMITTED,
                            "New Self-Appraisal Submitted",
                            f"{request.user.get_full_name()} has submitted their self-appraisal. It is now awaiting your review (Step {first_step.step_number}: {first_step.label}).",
                            appraisal
                        )
                else:
                    appraisal.status = Appraisal.SUBMITTED
            else:
                appraisal.current_step_number = 1
                appraisal.status = Appraisal.SUBMITTED
                if appraisal.supervisor:
                    from notifications.models import Notification
                    _send_notification(
                        appraisal.supervisor, request.user,
                        Notification.APPRAISAL_SUBMITTED,
                        "New Self-Appraisal Submitted",
                        f"{request.user.get_full_name()} has submitted their self-appraisal.",
                        appraisal
                    )

            appraisal.self_submitted_at = timezone.now()
            appraisal.save()

            messages.success(request, "Your self-appraisal has been submitted successfully!")
            return redirect('accounts:dashboard_redirect')
        else:
            messages.success(request, "Self-appraisal draft saved successfully.")
            return redirect('appraisals:self_appraisal_form')

    # --- GET: build sections with responses ---
    sections_with_responses = []
    for section in appraisee_sections:
        fields_data = []
        for field in section.fields.filter(filled_by=FormField.APPRAISEE).order_by('order'):
            resp = FormFieldResponse.objects.filter(
                appraisal=appraisal,
                field=field,
                responded_by=request.user,
                response_type=FormFieldResponse.PRIMARY,
            ).first()
            fields_data.append({'field': field, 'response': resp})
        if fields_data:
            sections_with_responses.append({'section': section, 'fields': fields_data})

    process = appraisal.active_process
    approval_steps = process.steps.all() if process else []

    context = {
        'cycle': active_cycle,
        'appraisal': appraisal,
        'is_editable': is_editable,
        'sections_with_responses': sections_with_responses,
        'approval_steps': approval_steps,
        'process': process,
        'FIELD_TYPE': {
            'NARRATIVE': FormField.NARRATIVE,
            'SCORE': FormField.SCORE,
            'SCORE_COMMENT': FormField.SCORE_COMMENT,
            'SINGLE_SELECT': FormField.SINGLE_SELECT,
            'MULTI_SELECT': FormField.MULTI_SELECT,
        },
    }
    return render(request, 'appraisals/self_appraisal_form.html', context)


@login_required
def my_appraisals(request):
    """Displays a list of all appraisals belonging to the currently logged-in user."""
    appraisals = (
        Appraisal.objects
        .filter(staff=request.user)
        .select_related('cycle', 'supervisor')
        .order_by('-cycle__start_date')
    )
    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()
    submitted_statuses = [
        Appraisal.SUBMITTED,
        Appraisal.AWAITING_STEP_REVIEW,
        Appraisal.RETURNED_TO_REVIEWER,
    ]
    approved_statuses = [Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED]

    context = {
        'appraisals': appraisals,
        'total_count': appraisals.count(),
        'submitted_count': appraisals.filter(status__in=submitted_statuses).count(),
        'approved_count': appraisals.filter(status__in=approved_statuses).count(),
        'active_cycle': active_cycle,
    }
    return render(request, 'appraisals/my_appraisals.html', context)


# ============================================================
# UNIVERSAL DYNAMIC STEP REVIEW
# ============================================================

@login_required
def step_review(request, pk):
    """
    Universal dynamic review view for all approver roles.

    Shows:
    1. All APPRAISEE-filled sections + responses (read-only)
    2. Fields assigned to the current reviewer's role (editable)
    3. Mode B: reviewer score/comment on appraisee fields

    Any reviewer role (Supervisor, HOD, Director, HR) lands here.
    Validates that the logged-in user is the assigned approver for the current step.
    """
    appraisal = get_object_or_404(Appraisal, pk=pk)

    current_assignment = appraisal.current_assignment
    is_hr_admin = request.user.role == CustomUser.HR_ADMIN
    is_current_approver = (
        current_assignment is not None and
        current_assignment.approver == request.user
    )
    has_any_assignment = appraisal.approval_assignments.filter(approver=request.user).exists()

    if not is_hr_admin and not is_current_approver and not has_any_assignment:
        messages.error(request, "You do not have access to review this appraisal.")
        return redirect('accounts:dashboard_redirect')

    is_editable = is_current_approver and appraisal.status in [
        Appraisal.SUBMITTED, Appraisal.AWAITING_STEP_REVIEW, Appraisal.RETURNED_TO_REVIEWER
    ]

    current_step = current_assignment.step if current_assignment else None

    # Map ApprovalStep to FormField.filled_by matches.
    # STEP_N values in the form builder always refer to the GENERAL process
    # step numbering, so we resolve them to roles via the general process.
    # This ensures that e.g. STEP_2 = HOD works even when reviewing an
    # appraisal that uses an override process where the HOD is at step 1.
    role_code = current_step.role_required if current_step else ''

    # Build allowed_filled_by_values: the set of filled_by codes this reviewer
    # is permitted to fill.
    #
    # STEP_N in the form builder is resolved as follows:
    #   1. Always include the reviewer's direct role code (e.g. HOD)
    #   2. Include STEP_N codes from the GENERAL process where the role matches
    #      (e.g. HOD matches STEP_2 in the general process)
    #   3. Include STEP_N for the reviewer's active step number ONLY if
    #      the general process doesn't assign that step to a DIFFERENT role
    #      (this handles override processes where step numbers shift)
    #
    # Example:
    #   General:  Step 1=Supervisor, Step 2=HOD, Step 3=Director, Step 4=HR
    #   Override: Step 1=HOD, Step 2=Director, Step 3=HR
    #   HOD at override step 1:
    #     -> STEP_2 (general process: HOD = step 2)
    #     -> STEP_1 (active step 1; general has SUPERVISOR there, but HOD IS
    #        the reviewer at step 1, so include it)
    #     -> HOD (direct role)
    #   Director at override step 2:
    #     -> STEP_3 (general process: Director = step 3)
    #     -> NOT STEP_2 (general process says STEP_2 = HOD, different role)
    #     -> DIRECTORATE (direct role)

    # Build general process role map first
    general_process = appraisal.cycle.approval_processes.filter(is_general=True).first()
    general_step_role_map = {}
    if general_process:
        for gstep in general_process.steps.all():
            general_step_role_map[f'STEP_{gstep.step_number}'] = gstep.role_required

    allowed_filled_by_values = set()

    # 1. Always include the reviewer's direct role code
    if role_code:
        allowed_filled_by_values.add(role_code)

    # 2. Include STEP_N codes from the GENERAL process where the role matches
    general_step_codes = [code for code, role in general_step_role_map.items() if role == role_code]
    allowed_filled_by_values.update(general_step_codes)

    # 3. Include STEP_N for the active process step number, but only when
    #    appropriate. If the general process assigns a DIFFERENT role at
    #    that step, only include it if that role is NOT present as a separate
    #    step in the active process (meaning this reviewer absorbs those duties).
    if current_step:
        active_step_code = f'STEP_{current_step.step_number}'
        general_role_at_step = general_step_role_map.get(active_step_code)
        if general_role_at_step is None or general_role_at_step == role_code:
            # Same role or step doesn't exist in general -> always include
            allowed_filled_by_values.add(active_step_code)
        else:
            # General process has a different role at this step number.
            # Only include if that role doesn't have its own step in the
            # active process (meaning this reviewer absorbs those duties).
            active_process = appraisal.active_process
            active_roles = set()
            if active_process:
                active_roles = set(
                    s.role_required for s in active_process.steps.all()
                )
            if general_role_at_step not in active_roles:
                allowed_filled_by_values.add(active_step_code)

    allowed_filled_by_values = [v for v in allowed_filled_by_values if v]
    reviewer_filled_by = role_code

    if request.method == 'POST':
        if not is_editable:
            messages.error(request, "This appraisal is not currently actionable by you.")
            return redirect('appraisals:step_review', pk=pk)

        action = request.POST.get('action')
        comments = request.POST.get('comments', '').strip()

        # --- Save reviewer's primary fields (assigned to this role or step) ---
        reviewer_fields = FormField.objects.filter(
            section__cycle=appraisal.cycle,
            filled_by__in=allowed_filled_by_values,
        )
        for field in reviewer_fields:
            resp, _ = FormFieldResponse.objects.get_or_create(
                appraisal=appraisal,
                field=field,
                responded_by=request.user,
                response_type=FormFieldResponse.PRIMARY,
            )
            post_key = f'field_{field.id}'
            ftype = field.field_type

            if ftype == FormField.NARRATIVE:
                resp.text_response = request.POST.get(post_key, '').strip()
            elif ftype == FormField.SCORE:
                val = request.POST.get(post_key, '').strip()
                try:
                    resp.score = Decimal(val) if val else None
                except InvalidOperation:
                    resp.score = None
                # Clamp to field min/max
                if resp.score is not None:
                    resp.score = max(field.min_score, min(field.max_score, resp.score))
            elif ftype == FormField.SCORE_COMMENT:
                val = request.POST.get(f'{post_key}_score', '').strip()
                try:
                    resp.score = Decimal(val) if val else None
                except InvalidOperation:
                    resp.score = None
                # Clamp to field min/max
                if resp.score is not None:
                    resp.score = max(field.min_score, min(field.max_score, resp.score))
                resp.text_response = request.POST.get(f'{post_key}_comment', '').strip()
            elif ftype == FormField.SINGLE_SELECT:
                selected = request.POST.get(post_key, '')
                resp.selected_options = [selected] if selected else []
            elif ftype == FormField.MULTI_SELECT:
                resp.selected_options = request.POST.getlist(post_key)

            evidence = request.FILES.get(f'{post_key}_evidence')
            if evidence:
                resp.evidence_file = evidence
            resp.save()

        # --- Mode B: Save reviewer scores/comments on appraisee fields ---
        appraisee_fields_mode_b = FormField.objects.filter(
            section__cycle=appraisal.cycle,
            filled_by=FormField.APPRAISEE,
        ).filter(
            models.Q(reviewer_can_score=True, reviewer_score_role__in=allowed_filled_by_values) |
            models.Q(reviewer_can_comment=True, reviewer_comment_role__in=allowed_filled_by_values)
        )

        for field in appraisee_fields_mode_b.distinct():
            # Reviewer score on appraisee field
            if field.reviewer_can_score and field.reviewer_score_role in allowed_filled_by_values:
                score_resp, _ = FormFieldResponse.objects.get_or_create(
                    appraisal=appraisal,
                    field=field,
                    responded_by=request.user,
                    response_type=FormFieldResponse.REVIEWER_SCORE,
                )
                val = request.POST.get(f'modb_score_{field.id}', '').strip()
                try:
                    score_resp.score = Decimal(val) if val else None
                except InvalidOperation:
                    score_resp.score = None
                # Clamp to 0..reviewer_score_max
                if score_resp.score is not None:
                    score_resp.score = max(Decimal('0'), min(field.reviewer_score_max, score_resp.score))
                score_resp.save()

            # Reviewer comment on appraisee field
            if field.reviewer_can_comment and field.reviewer_comment_role in allowed_filled_by_values:
                comment_resp, _ = FormFieldResponse.objects.get_or_create(
                    appraisal=appraisal,
                    field=field,
                    responded_by=request.user,
                    response_type=FormFieldResponse.REVIEWER_COMMENT,
                )
                comment_resp.text_response = request.POST.get(f'modb_comment_{field.id}', '').strip()
                comment_resp.save()

        current_assignment.comments = comments

        if action == 'save_draft':
            current_assignment.save()
            messages.success(request, "Draft saved successfully.")
            return redirect('appraisals:step_review', pk=pk)

        elif action == 'approve':
            current_assignment.status = AppraisalApprovalAssignment.APPROVED
            current_assignment.actioned_at = timezone.now()
            current_assignment.save()

            # Advance workflow to next step
            _advance_appraisal(appraisal, current_assignment, request.user)

            messages.success(request, "Appraisal approved and advanced to the next step.")
            return redirect('appraisals:review_queue')

        elif action == 'return':
            return_comment = request.POST.get('return_comment', '').strip() or comments
            _return_appraisal(appraisal, current_assignment, request.user, return_comment)
            messages.warning(request, "Appraisal returned for revision.")
            return redirect('appraisals:review_queue')

    # GET: Prepare sections data for template
    appraisee_sections_data = []
    for section in FormSection.objects.filter(cycle=appraisal.cycle).order_by('order'):
        fields_data = []
        for field in section.fields.filter(filled_by=FormField.APPRAISEE).order_by('order'):
            primary_resp = FormFieldResponse.objects.filter(
                appraisal=appraisal,
                field=field,
                responded_by=appraisal.staff,
                response_type=FormFieldResponse.PRIMARY,
            ).first()

            # Mode B: check if this reviewer has score/comment on this field
            mode_b_score_resp = None
            mode_b_comment_resp = None
            if allowed_filled_by_values:
                if field.reviewer_can_score and field.reviewer_score_role in allowed_filled_by_values:
                    mode_b_score_resp = FormFieldResponse.objects.filter(
                        appraisal=appraisal, field=field,
                        responded_by=request.user,
                        response_type=FormFieldResponse.REVIEWER_SCORE,
                    ).first()
                if field.reviewer_can_comment and field.reviewer_comment_role in allowed_filled_by_values:
                    mode_b_comment_resp = FormFieldResponse.objects.filter(
                        appraisal=appraisal, field=field,
                        responded_by=request.user,
                        response_type=FormFieldResponse.REVIEWER_COMMENT,
                    ).first()

            fields_data.append({
                'field': field,
                'response': primary_resp,
                'mode_b_score_resp': mode_b_score_resp,
                'mode_b_comment_resp': mode_b_comment_resp,
                'can_score': (field.reviewer_can_score and field.reviewer_score_role in allowed_filled_by_values),
                'can_comment': (field.reviewer_can_comment and field.reviewer_comment_role in allowed_filled_by_values),
            })
        if fields_data:
            appraisee_sections_data.append({'section': section, 'fields': fields_data})

    # Reviewer's own fields (editable)
    reviewer_sections_data = []
    for section in FormSection.objects.filter(cycle=appraisal.cycle).order_by('order'):
        fields_data = []
        for field in section.fields.filter(filled_by__in=allowed_filled_by_values).order_by('order') if allowed_filled_by_values else []:
            resp = FormFieldResponse.objects.filter(
                appraisal=appraisal,
                field=field,
                responded_by=request.user,
                response_type=FormFieldResponse.PRIMARY,
            ).first()
            fields_data.append({'field': field, 'response': resp})
        if fields_data:
            reviewer_sections_data.append({'section': section, 'fields': fields_data})

    # Previous reviewers' fields (read-only) — shows scores/comments from
    # earlier steps so the current reviewer has full context.
    previous_reviewer_sections_data = []
    # Collect all filled_by values that are NOT appraisee and NOT current reviewer
    all_step_and_role_codes = set()
    if general_step_role_map:
        all_step_and_role_codes.update(general_step_role_map.keys())
        all_step_and_role_codes.update(general_step_role_map.values())
    # Also include direct role codes
    for rc in ['SUPERVISOR', 'HOD', 'DIRECTORATE', 'HR_ADMIN']:
        all_step_and_role_codes.add(rc)
    # Remove current reviewer's codes and APPRAISEE
    prev_codes = all_step_and_role_codes - set(allowed_filled_by_values) - {'APPRAISEE'}

    for section in FormSection.objects.filter(cycle=appraisal.cycle).order_by('order'):
        fields_data = []
        for field in section.fields.filter(filled_by__in=prev_codes).order_by('order') if prev_codes else []:
            # Find the response from whoever filled it
            resp = FormFieldResponse.objects.filter(
                appraisal=appraisal,
                field=field,
                response_type=FormFieldResponse.PRIMARY,
            ).first()
            fields_data.append({'field': field, 'response': resp})
        if fields_data:
            previous_reviewer_sections_data.append({'section': section, 'fields': fields_data})

    all_assignments = appraisal.approval_assignments.select_related(
        'step', 'approver'
    ).order_by('step__step_number')

    return_reason_entries = [
        assignment for assignment in all_assignments
        if assignment.status == AppraisalApprovalAssignment.RETURNED and assignment.comments
    ]
    reviewer_comment_entries = [
        assignment for assignment in all_assignments
        if assignment.comments
        and assignment.status != AppraisalApprovalAssignment.RETURNED
        and (
            not assignment.approver_id or assignment.approver_id != request.user.id
        )
    ]

    context = {
        'appraisal': appraisal,
        'current_assignment': current_assignment,
        'current_step': current_step,
        'is_editable': is_editable,
        'is_hr_admin': is_hr_admin,
        'appraisee_sections_data': appraisee_sections_data,
        'previous_reviewer_sections_data': previous_reviewer_sections_data,
        'reviewer_sections_data': reviewer_sections_data,
        'all_assignments': all_assignments,
        'return_reason_entries': return_reason_entries,
        'reviewer_comment_entries': reviewer_comment_entries,
        'active_process': appraisal.active_process,
        'reviewer_filled_by': reviewer_filled_by,
        'FIELD_TYPE': {
            'NARRATIVE': FormField.NARRATIVE,
            'SCORE': FormField.SCORE,
            'SCORE_COMMENT': FormField.SCORE_COMMENT,
            'SINGLE_SELECT': FormField.SINGLE_SELECT,
            'MULTI_SELECT': FormField.MULTI_SELECT,
        },
    }
    return render(request, 'appraisals/step_review.html', context)


@login_required
def acknowledge_appraisal(request, pk):
    """
    Staff acknowledges their final approved appraisal result.
    """
    appraisal = get_object_or_404(Appraisal, pk=pk, staff=request.user)

    if appraisal.status not in [Appraisal.APPROVED]:
        messages.error(request, "This appraisal is not yet available for acknowledgement.")
        return redirect('appraisals:my_appraisals')

    if request.method == 'POST':
        appraisal.status = Appraisal.STAFF_ACKNOWLEDGED
        appraisal.staff_acknowledged_at = timezone.now()
        appraisal.save()
        messages.success(request, "You have acknowledged your appraisal result. Thank you.")
        return redirect('appraisals:appraisal_result', pk=pk)

    return redirect('appraisals:appraisal_result', pk=pk)


@login_required
def appraisal_result(request, pk):
    """
    Displays the final result of an appraisal to the staff member.
    Also shown after acknowledgement.
    """
    appraisal = get_object_or_404(Appraisal, pk=pk)

    if not _user_can_view_appraisal(request, appraisal):
        messages.error(request, "You do not have permission to view this appraisal.")
        return redirect('accounts:dashboard_redirect')

    context = _build_appraisal_result_context(request, appraisal)
    return render(request, 'appraisals/appraisal_result.html', context)


@login_required
def download_appraisal_result(request, pk):
    """Download a standalone HTML report for an appraisal the user can view."""
    appraisal = get_object_or_404(Appraisal, pk=pk)

    if not _user_can_view_appraisal(request, appraisal):
        messages.error(request, "You do not have permission to download this appraisal.")
        return redirect('accounts:dashboard_redirect')

    context = _build_appraisal_result_context(request, appraisal)
    html = render_to_string('appraisals/appraisal_result_download.html', context, request=request)

    staff_slug = slugify(appraisal.staff.get_full_name() or appraisal.staff.username) or f"staff-{appraisal.staff_id}"
    cycle_slug = slugify(appraisal.cycle.name) or f"cycle-{appraisal.cycle_id}"
    filename = f"appraisal-{staff_slug}-{cycle_slug}.html"

    response = HttpResponse(html, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


# ============================================================
# TEAM / DEPARTMENT LIST VIEWS (for reviewers)
# ============================================================

@login_required
def my_review_queue(request):
    """
    Shows all appraisals where the current user is the assigned approver
    for the current pending step.
    """
    REVIEWER_ROLES = [CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.DIRECTORATE, CustomUser.HR_ADMIN]
    if request.user.role not in REVIEWER_ROLES:
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')

    active_cycles = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE)
    active_cycle = active_cycles.first()  # For template context (cycle selector)

    # Pending assignments for this reviewer across ALL active cycles
    pending_assignments = AppraisalApprovalAssignment.objects.filter(
        approver=request.user,
        status=AppraisalApprovalAssignment.PENDING,
    ).select_related('appraisal__staff', 'appraisal__cycle', 'step')

    if active_cycles.exists():
        pending_assignments = pending_assignments.filter(appraisal__cycle__in=active_cycles)

    # Filter to only assignments where this step is the CURRENT step
    ACTIONABLE_STATUSES = [
        Appraisal.SUBMITTED,
        Appraisal.AWAITING_STEP_REVIEW,
        Appraisal.RETURNED_TO_REVIEWER,  # Previous reviewer must re-review after HOD/Director return
    ]
    current_pending = [
        a for a in pending_assignments
        if a.appraisal.current_step_number == a.step.step_number and
           a.appraisal.status in ACTIONABLE_STATUSES
    ]
    current_pending.sort(
        key=lambda assignment: _appraisal_recency_timestamp(assignment.appraisal),
        reverse=True,
    )

    # Appraisal IDs currently in the user's pending queue — exclude from history
    pending_appraisal_ids = {a.appraisal_id for a in current_pending}

    # All past assignments (reviewed history) — APPROVED or RETURNED, excluding currently pending
    # We cast a wide net: all cycles so nothing disappears after approval
    past_assignments = AppraisalApprovalAssignment.objects.filter(
        approver=request.user,
        status__in=[AppraisalApprovalAssignment.APPROVED, AppraisalApprovalAssignment.RETURNED],
    ).exclude(
        appraisal_id__in=pending_appraisal_ids
    ).select_related('appraisal__staff', 'appraisal__cycle', 'step').order_by('-actioned_at')[:50]

    context = {
        'current_pending': current_pending,
        'past_assignments': past_assignments,
        'past_actions': past_assignments,
        'active_cycle': active_cycle,
    }
    return render(request, 'appraisals/review_queue.html', context)


@login_required
def team_list(request):
    """
    Displays all direct reports of the supervisor and their appraisal status.
    Supports GET-based search (name/staff ID) and status filter.
    """
    if request.user.role not in [CustomUser.SUPERVISOR, CustomUser.HOD]:
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')

    team = CustomUser.objects.filter(supervisor=request.user).select_related('department')
    active_cycles = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE)

    # --- Read filter params ---
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    team_data = []
    for member in team:
        appraisal = None
        if active_cycles.exists():
            appraisal = Appraisal.objects.filter(staff=member, cycle__in=active_cycles).order_by('-created_at').first()
        team_data.append({'member': member, 'appraisal': appraisal})

    # --- Apply search filter ---
    if search_q:
        q_lower = search_q.lower()
        team_data = [
            item for item in team_data
            if q_lower in item['member'].get_full_name().lower()
            or q_lower in (item['member'].staff_id or '').lower()
            or q_lower in (item['member'].designation or '').lower()
        ]

    # --- Apply status filter ---
    if status_filter == 'not_started':
        team_data = [
            item for item in team_data
            if not item['appraisal'] or item['appraisal'].status in [
                Appraisal.NOT_STARTED, Appraisal.DRAFT
            ]
        ]
    elif status_filter == 'submitted':
        team_data = [
            item for item in team_data
            if item['appraisal'] and item['appraisal'].status in [
                Appraisal.SUBMITTED, Appraisal.AWAITING_STEP_REVIEW, Appraisal.RETURNED_TO_REVIEWER
            ]
        ]
    elif status_filter == 'returned':
        team_data = [
            item for item in team_data
            if item['appraisal'] and item['appraisal'].status in [
                Appraisal.RETURNED_TO_STAFF, Appraisal.RETURNED_TO_REVIEWER
            ]
        ]
    elif status_filter == 'approved':
        team_data = [
            item for item in team_data
            if item['appraisal'] and item['appraisal'].status in [
                Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED, Appraisal.ARCHIVED
            ]
        ]

    team_data.sort(key=_team_appraisal_sort_key)

    context = {
        'team_data': team_data,
        'active_cycle': active_cycles.first(),
        'search_q': search_q,
        'status_filter': status_filter,
        'total_count': CustomUser.objects.filter(supervisor=request.user).count(),
    }
    return render(request, 'appraisals/team_list.html', context)


@login_required
def department_appraisals(request):
    """Displays all staff in the HOD's department and their appraisal status."""
    if request.user.role != CustomUser.HOD:
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')

    dept_staff = CustomUser.objects.filter(department=request.user.department)
    active_cycles = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE)

    dept_data = []
    for member in dept_staff:
        appraisal = None
        if active_cycles.exists():
            appraisal = Appraisal.objects.filter(staff=member, cycle__in=active_cycles).order_by('-created_at').first()
        dept_data.append({'member': member, 'appraisal': appraisal})

    context = {'dept_data': dept_data, 'active_cycle': active_cycles.first()}
    return render(request, 'appraisals/department_list.html', context)


@login_required
def department_reports(request):
    """Displays a summary report for the HOD's department."""
    if request.user.role != CustomUser.HOD:
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')

    dept_staff = CustomUser.objects.filter(department=request.user.department)
    active_cycles = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE)

    total_staff = dept_staff.count()
    completed_appraisals = 0
    in_progress = 0
    not_started = 0

    if active_cycles.exists():
        appraisals = Appraisal.objects.filter(staff__in=dept_staff, cycle__in=active_cycles)
        for appraisal in appraisals:
            if appraisal.status in [Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED, Appraisal.ARCHIVED]:
                completed_appraisals += 1
            elif appraisal.status in [Appraisal.NOT_STARTED, Appraisal.DRAFT]:
                not_started += 1
            else:
                in_progress += 1
        
        # Any staff without an appraisal record for the active cycles count as not started
        staff_with_appraisal = appraisals.values_list('staff_id', flat=True).distinct().count()
        not_started += (total_staff - staff_with_appraisal)
    else:
        not_started = total_staff

    context = {
        'total_staff': total_staff,
        'completed_appraisals': completed_appraisals,
        'in_progress': in_progress,
        'not_started': not_started,
        'active_cycle': active_cycles.first(),
    }
    return render(request, 'appraisals/department_reports.html', context)


# ============================================================
# LEGACY VIEWS (compatibility redirects)
# ============================================================

@login_required
def supervisor_review(request, pk):
    """Legacy redirect to universal step_review."""
    return step_review(request, pk)


@login_required
def hod_review(request, pk):
    """Legacy redirect to universal step_review."""
    return step_review(request, pk)
