from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from appraisals.models import (
    AppraisalCycle, KPICategory, CompetencyCategory, NarrativeField,
    ApprovalProcess, ApprovalStep, AppraisalApprovalAssignment, Appraisal,
    KPIItem, CompetencyItem, NarrativeResponse, KPIScore, CompetencyScore,
    FormSection, FormField,
)
import json


def hr_required(view_func):
    """Decorator to restrict view to HR_ADMIN role only."""
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'HR_ADMIN':
            messages.error(request, "Access denied. HR Administrators only.")
            return redirect('accounts:dashboard_redirect')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return login_required(wrapper)


# ============================================================
# DASHBOARD
# ============================================================

@hr_required
def dashboard(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()
    pending_assignments = 0
    awaiting_my_review = 0
    appraisal_stats = {}

    if active_cycle:
        appraisals = active_cycle.appraisals.all()
        appraisal_stats = {
            'total': appraisals.count(),
            'not_started': appraisals.filter(status='NOT_STARTED').count(),
            'draft': appraisals.filter(status='DRAFT').count(),
            'submitted': appraisals.filter(status='SUBMITTED').count(),
            'in_review': appraisals.filter(status='AWAITING_STEP_REVIEW').count(),
            'approved': appraisals.filter(status='APPROVED').count(),
            'acknowledged': appraisals.filter(status='STAFF_ACKNOWLEDGED').count(),
        }
        # Assignments with no approver set yet (need attention)
        pending_assignments = AppraisalApprovalAssignment.objects.filter(
            appraisal__cycle=active_cycle,
            approver__isnull=True,
            status='PENDING'
        ).count()

        ACTIONABLE_STATUSES = [
            Appraisal.SUBMITTED,
            Appraisal.AWAITING_STEP_REVIEW,
            Appraisal.RETURNED_TO_REVIEWER,
        ]
        awaiting_my_review = sum(
            1 for assignment in AppraisalApprovalAssignment.objects.filter(
                appraisal__cycle=active_cycle,
                approver=request.user,
                status=AppraisalApprovalAssignment.PENDING,
                appraisal__status__in=ACTIONABLE_STATUSES,
            ).select_related('appraisal', 'step')
            if assignment.appraisal.current_step_number == assignment.step.step_number
        )

    context = {
        'active_cycle': active_cycle,
        'active_cycle_count': AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).count(),
        'total_staff': User.objects.exclude(role='HR_ADMIN').count(),
        'appraisal_stats': appraisal_stats,
        'pending_assignments': pending_assignments,
        'awaiting_my_review': awaiting_my_review,
    }
    return render(request, 'hr_admin/dashboard.html', context)


# ============================================================
# CYCLE MANAGEMENT
# ============================================================

@hr_required
def cycle_list(request):
    cycles = AppraisalCycle.objects.all().order_by('-created_at')
    return render(request, 'hr_admin/cycle_list.html', {'cycles': cycles})


@hr_required
def cycle_create(request):
    from branches.models import Branch

    if request.method == 'POST':
        name = request.POST.get('name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        scoring_scale = request.POST.get('scoring_scale', 5)
        branch_id = request.POST.get('branch')

        branch = get_object_or_404(Branch, pk=branch_id) if branch_id else None

        cycle = AppraisalCycle.objects.create(
            name=name,
            start_date=start_date,
            end_date=end_date,
            scoring_scale=scoring_scale,
            branch=branch,
            status=AppraisalCycle.DRAFT,
            created_by=request.user,
        )

        target_depts = request.POST.getlist('target_departments')
        if target_depts:
            cycle.target_departments.set(target_depts)

        target_users = request.POST.getlist('target_staff')
        if target_users:
            cycle.target_staff.set(target_users)

        if not target_depts and not target_users and branch:
            # Auto-target all active users in this branch
            branch_members = branch.members.filter(
                is_active=True,
                role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.DIRECTORATE]
            )
            cycle.target_staff.set(branch_members)

        messages.success(request, f"Cycle '{cycle.name}' created. Now configure the fields.")
        return redirect('hr_admin:cycle_edit', pk=cycle.pk)

    from departments.models import Department
    from accounts.models import CustomUser

    context = {
        'branches': Branch.objects.all(),
        'departments': Department.objects.all(),
        'staff': CustomUser.objects.filter(
            is_active=True,
            role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.DIRECTORATE]
        ),
        'target_dept_ids': [],
        'target_staff_ids': []
    }
    return render(request, 'hr_admin/cycle_form.html', context)


@hr_required
def cycle_detail(request, pk):
    cycle = get_object_or_404(AppraisalCycle, pk=pk)
    return render(request, 'hr_admin/cycle_detail.html', {'cycle': cycle})


@hr_required
def cycle_edit(request, pk):
    cycle = get_object_or_404(AppraisalCycle, pk=pk)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # --- Basic cycle fields ---
            cycle.name = data.get('name', cycle.name)
            if data.get('start_date'):
                cycle.start_date = data.get('start_date')
            if data.get('end_date'):
                cycle.end_date = data.get('end_date')
            if data.get('scoring_scale'):
                cycle.scoring_scale = data.get('scoring_scale')
            if data.get('status'):
                cycle.status = data.get('status')
            cycle.save()

            # --- Form Sections & Fields ---
            saved_sections = []
            for sIdx, sec_data in enumerate(data.get('form_sections', [])):
                sec_id = sec_data.get('id')

                if sec_data.get('deleted'):
                    if sec_id:
                        FormSection.objects.filter(id=sec_id, cycle=cycle).delete()
                    continue

                sec, _ = FormSection.objects.update_or_create(
                    id=sec_id if sec_id else None,
                    defaults={
                        'cycle': cycle,
                        'name': sec_data.get('name', ''),
                        'description': sec_data.get('description', ''),
                        'section_weight': sec_data.get('section_weight', 0),
                        'order': sIdx,
                    }
                )

                saved_fields = []
                for fIdx, fld_data in enumerate(sec_data.get('fields', [])):
                    fld_id = fld_data.get('id')

                    if fld_data.get('deleted'):
                        if fld_id:
                            FormField.objects.filter(id=fld_id, section=sec).delete()
                        continue

                    fld, _ = FormField.objects.update_or_create(
                        id=fld_id if fld_id else None,
                        defaults={
                            'section': sec,
                            'label': fld_data.get('label', ''),
                            'description': fld_data.get('description', ''),
                            'field_type': fld_data.get('field_type', FormField.NARRATIVE),
                            'filled_by': fld_data.get('filled_by', FormField.APPRAISEE),
                            'max_score': fld_data.get('max_score', 10),
                            'min_score': fld_data.get('min_score', 0),
                            'options': fld_data.get('options', []),
                            'reviewer_can_score': fld_data.get('reviewer_can_score', False),
                            'reviewer_score_role': fld_data.get('reviewer_score_role', ''),
                            'reviewer_score_max': fld_data.get('reviewer_score_max', 10),
                            'reviewer_can_comment': fld_data.get('reviewer_can_comment', False),
                            'reviewer_comment_role': fld_data.get('reviewer_comment_role', ''),
                            'is_required': fld_data.get('is_required', True),
                            'order': fIdx,
                        }
                    )
                    saved_fields.append({'id': fld.id, 'label': fld.label})

                saved_sections.append({'id': sec.id, 'name': sec.name, 'fields': saved_fields})

            # If cycle is now ACTIVE, initialize appraisals
            if cycle.status == AppraisalCycle.ACTIVE:
                _initialize_cycle_appraisals(cycle)

            return JsonResponse({
                'status': 'success',
                'message': 'Cycle saved successfully.',
                'sections': saved_sections,
            })

        except Exception as e:
            import traceback
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # --- GET: build form_sections_json for the template ---
    sections_qs = cycle.form_sections.prefetch_related('fields').order_by('order')
    form_sections_json = json.dumps([
        {
            'id': sec.id,
            'name': sec.name,
            'description': sec.description,
            'section_weight': float(sec.section_weight),
            'order': sec.order,
            'deleted': False,
            'fields': [
                {
                    'id': fld.id,
                    'label': fld.label,
                    'description': fld.description,
                    'field_type': fld.field_type,
                    'filled_by': fld.filled_by,
                    'max_score': float(fld.max_score),
                    'min_score': float(fld.min_score),
                    'options': fld.options,
                    'reviewer_can_score': fld.reviewer_can_score,
                    'reviewer_score_role': fld.reviewer_score_role,
                    'reviewer_score_max': float(fld.reviewer_score_max),
                    'reviewer_can_comment': fld.reviewer_can_comment,
                    'reviewer_comment_role': fld.reviewer_comment_role,
                    'is_required': fld.is_required,
                    'order': fld.order,
                    'deleted': False,
                }
                for fld in sec.fields.order_by('order')
            ],
        }
        for sec in sections_qs
    ])

    return render(request, 'hr_admin/cycle_builder.html', {
        'cycle': cycle,
        'form_sections_json': form_sections_json,
    })


# ============================================================
# APPROVAL PROCESS MANAGEMENT
# ============================================================

@hr_required
def approval_process_list(request, cycle_pk):
    """List all approval processes for a cycle (general + overrides)."""
    cycle = get_object_or_404(AppraisalCycle, pk=cycle_pk)
    processes = cycle.approval_processes.prefetch_related('steps').order_by('-is_general', 'name')

    context = {
        'cycle': cycle,
        'processes': processes,
        'general_process': cycle.general_approval_process,
    }
    return render(request, 'hr_admin/approval_process_list.html', context)


@hr_required
def approval_process_create(request, cycle_pk, process_pk=None):
    """Create or edit an approval process with its steps (AJAX + regular POST)."""
    cycle = get_object_or_404(AppraisalCycle, pk=cycle_pk)
    process = None
    if process_pk:
        process = get_object_or_404(ApprovalProcess, pk=process_pk, cycle=cycle)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            process_name = data.get('name', '').strip()
            is_general = data.get('is_general', False)
            steps_data = data.get('steps', [])

            if not process_name:
                return JsonResponse({'status': 'error', 'message': 'Process name is required.'}, status=400)

            if not steps_data:
                return JsonResponse({'status': 'error', 'message': 'At least one step is required.'}, status=400)

            # If marking as general, unmark any existing general process
            if is_general:
                ApprovalProcess.objects.filter(cycle=cycle, is_general=True).update(is_general=False)

            if process:
                process.name = process_name
                process.is_general = is_general
                process.save()
                # Clear existing steps and rebuild
                process.steps.all().delete()
            else:
                process = ApprovalProcess.objects.create(
                    cycle=cycle,
                    name=process_name,
                    is_general=is_general,
                    created_by=request.user,
                )

            # Create steps
            for step_data in steps_data:
                ApprovalStep.objects.create(
                    process=process,
                    step_number=step_data.get('step_number'),
                    label=step_data.get('label', ''),
                    role_required=step_data.get('role_required', 'SUPERVISOR'),
                    action_label_approve=step_data.get('action_label_approve', 'Approve & Forward'),
                    action_label_return=step_data.get('action_label_return', 'Return for Revision'),
                    can_score=step_data.get('can_score', True),
                )

            # If cycle is already active, create assignments for any appraisals missing them
            if cycle.status == AppraisalCycle.ACTIVE and is_general:
                _sync_assignments_for_process(cycle, process)

            return JsonResponse({
                'status': 'success',
                'message': f'Process "{process.name}" saved successfully.',
                'process_id': process.pk,
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # GET — render builder
    role_choices = ApprovalStep.ROLE_CHOICES
    context = {
        'cycle': cycle,
        'process': process,
        'role_choices': role_choices,
        'steps_json': json.dumps([
            {
                'step_number': s.step_number,
                'label': s.label,
                'role_required': s.role_required,
                'action_label_approve': s.action_label_approve,
                'action_label_return': s.action_label_return,
                'can_score': s.can_score,
            } for s in process.steps.all()
        ] if process else []),
        'process_json': json.dumps({
            'name': process.name if process else '',
            'is_general': process.is_general if process else False,
        } if process else {}),
    }
    return render(request, 'hr_admin/approval_process_builder.html', context)


@hr_required
def approval_process_delete(request, cycle_pk, process_pk):
    """Delete an approval process (only if no appraisals are using it as override)."""
    cycle = get_object_or_404(AppraisalCycle, pk=cycle_pk)
    process = get_object_or_404(ApprovalProcess, pk=process_pk, cycle=cycle)

    if request.method == 'POST':
        if process.is_general:
            messages.error(request, "Cannot delete the general process. Designate another as general first.")
        elif process.override_appraisals.exists():
            count = process.override_appraisals.count()
            messages.error(request, f"Cannot delete — {count} appraisal(s) use this as their override process.")
        else:
            process_name = process.name
            process.delete()
            messages.success(request, f"Process '{process_name}' deleted.")

    return redirect('hr_admin:approval_process_list', cycle_pk=cycle_pk)


@hr_required
def assign_approvers(request, cycle_pk):
    """
    UI for assigning specific approver users to each step for each appraisal
    in a cycle. Supports bulk auto-assign and individual overrides.
    """
    cycle = get_object_or_404(AppraisalCycle, pk=cycle_pk)
    from accounts.models import CustomUser

    if request.method == 'POST':
        # Handle bulk auto-assign
        if request.POST.get('action') == 'bulk_auto_assign':
            step_pk = request.POST.get('step_pk')
            rule = request.POST.get('rule', 'supervisor')  # 'supervisor' or 'specific_user'
            specific_user_pk = request.POST.get('specific_user')

            assignments = AppraisalApprovalAssignment.objects.filter(
                step__pk=step_pk,
                appraisal__cycle=cycle
            ).select_related('appraisal__staff')

            assigned_count = 0
            for assignment in assignments:
                if rule == 'supervisor' and assignment.appraisal.staff.supervisor:
                    assignment.approver = assignment.appraisal.staff.supervisor
                    assignment.save()
                    assigned_count += 1
                elif rule == 'specific_user' and specific_user_pk:
                    try:
                        user = CustomUser.objects.get(pk=specific_user_pk)
                        assignment.approver = user
                        assignment.save()
                        assigned_count += 1
                    except CustomUser.DoesNotExist:
                        pass

            messages.success(request, f"{assigned_count} approver(s) auto-assigned successfully.")
            return redirect('hr_admin:assign_approvers', cycle_pk=cycle_pk)

        # Handle individual assignment saves
        for key, value in request.POST.items():
            if key.startswith('assignment_'):
                try:
                    assignment_pk = int(key.split('_')[1])
                    assignment = AppraisalApprovalAssignment.objects.get(pk=assignment_pk)
                    if value:
                        user = CustomUser.objects.get(pk=value)
                        assignment.approver = user
                    else:
                        assignment.approver = None
                    assignment.save()
                except (AppraisalApprovalAssignment.DoesNotExist, CustomUser.DoesNotExist, ValueError):
                    pass

        messages.success(request, "Approver assignments saved successfully.")
        return redirect('hr_admin:assign_approvers', cycle_pk=cycle_pk)

    # GET — build the assignment table
    general_process = cycle.general_approval_process
    if not general_process:
        messages.warning(request, "No general approval process defined for this cycle. Please create one first.")
        return redirect('hr_admin:approval_process_list', cycle_pk=cycle_pk)

    from django.db.models import Case, When, Value, IntegerField
    steps = general_process.steps.all()
    appraisals = cycle.appraisals.select_related(
        'staff', 'staff__department', 'override_process'
    ).annotate(
        role_order=Case(
            When(staff__role='STAFF', then=Value(1)),
            When(staff__role='SUPERVISOR', then=Value(2)),
            When(staff__role='HOD', then=Value(3)),
            When(staff__role='DIRECTORATE', then=Value(4)),
            default=Value(5),
            output_field=IntegerField(),
        )
    ).order_by('role_order', 'override_process__id', 'staff__last_name', 'staff__first_name')

    # Get all possible approvers grouped by role
    role_users = {}
    for role_code, role_label in ApprovalStep.ROLE_CHOICES:
        role_users[role_code] = CustomUser.objects.filter(role=role_code, is_active=True)

    # Build assignment map: {appraisal_pk: {step_number: assignment}}
    assignments_map = {}
    for appraisal in appraisals:
        assignments_map[appraisal.pk] = {}
        active_proc = appraisal.active_process
        if active_proc:
            for step in active_proc.steps.all():
                assignment = appraisal.approval_assignments.filter(step=step).first()
                if not assignment:
                    # Create missing assignment
                    assignment = AppraisalApprovalAssignment.objects.create(
                        appraisal=appraisal, step=step,
                    )
                assignments_map[appraisal.pk][step.step_number] = assignment

    context = {
        'cycle': cycle,
        'general_process': general_process,
        'steps': steps,
        'appraisals': appraisals,
        'assignments_map': assignments_map,
        'role_users': role_users,
        'all_active_users': cycle.branch.members.filter(is_active=True).order_by('last_name', 'first_name') if cycle.branch else CustomUser.objects.filter(is_active=True).order_by('last_name', 'first_name'),
    }
    return render(request, 'hr_admin/assign_approvers.html', context)


@hr_required
def api_assign_approver(request, cycle_pk):
    if request.method == 'POST':
        from accounts.models import CustomUser
        try:
            data = json.loads(request.body)
            appraisal_id = data.get('appraisal_id')
            step_id = data.get('step_id')
            assignee_id = data.get('assignee_id')

            assignment = AppraisalApprovalAssignment.objects.get(
                appraisal_id=appraisal_id, step_id=step_id, appraisal__cycle_id=cycle_pk
            )
            
            if assignee_id:
                assignment.approver = CustomUser.objects.get(pk=assignee_id)
            else:
                assignment.approver = None
            assignment.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@hr_required
def api_bulk_assign(request, cycle_pk):
    if request.method == 'POST':
        from accounts.models import CustomUser
        try:
            data = json.loads(request.body)
            step_id = data.get('step_id')
            logic = data.get('logic')
            appraisal_ids = data.get('appraisal_ids')

            # Get the target step to know which role we're bulk-assigning
            target_step = get_object_or_404(ApprovalStep, pk=step_id)
            target_role = target_step.role_required

            # Resolve the specific person once if logic is a user ID
            specific_user = None
            if logic and logic not in ('supervisor', 'hod'):
                try:
                    specific_user = CustomUser.objects.get(pk=int(logic))
                except (ValueError, CustomUser.DoesNotExist):
                    return JsonResponse({'status': 'error', 'message': 'Selected user not found.'}, status=400)

            # Get all appraisals in this cycle (filtered by visible if appraisal_ids given)
            from appraisals.models import Appraisal
            appraisals_qs = Appraisal.objects.filter(cycle_id=cycle_pk).select_related(
                'staff', 'staff__department', 'staff__supervisor',
                'override_process'
            ).prefetch_related('approval_assignments__step')

            if appraisal_ids is not None:
                appraisals_qs = appraisals_qs.filter(pk__in=appraisal_ids)

            count = 0
            for appraisal in appraisals_qs:
                # Find the assignment in this appraisal's active process that matches the target role
                matching_assignment = appraisal.approval_assignments.filter(
                    step__role_required=target_role
                ).select_related('step').first()

                if not matching_assignment:
                    continue

                if logic == 'supervisor':
                    if appraisal.staff.supervisor:
                        matching_assignment.approver = appraisal.staff.supervisor
                        matching_assignment.save()
                        count += 1
                elif logic == 'hod':
                    department = appraisal.staff.department
                    if department and department.hod:
                        matching_assignment.approver = department.hod
                        matching_assignment.save()
                        count += 1
                elif specific_user:
                    matching_assignment.approver = specific_user
                    matching_assignment.save()
                    count += 1

            return JsonResponse({'status': 'success', 'message': f'Assigned {count} approvers.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)



@hr_required
def set_override_process(request, appraisal_pk):
    """Assign or remove an override approval process for a specific staff's appraisal."""
    appraisal = get_object_or_404(Appraisal, pk=appraisal_pk)
    cycle = appraisal.cycle

    if request.method == 'POST':
        process_pk = request.POST.get('override_process')
        if process_pk:
            override = get_object_or_404(ApprovalProcess, pk=process_pk, cycle=cycle)
            appraisal.override_process = override
            appraisal.save()

            # Initialize assignment records for the override process
            for step in override.steps.all():
                AppraisalApprovalAssignment.objects.get_or_create(
                    appraisal=appraisal, step=step
                )
            messages.success(request, f"Override process set for {appraisal.staff.get_full_name()}.")
        else:
            appraisal.override_process = None
            appraisal.save()
            messages.success(request, f"Override process removed. Using general process.")

        return redirect('hr_admin:assign_approvers', cycle_pk=cycle.pk)

    processes = cycle.approval_processes.filter(is_general=False)
    context = {
        'appraisal': appraisal,
        'cycle': cycle,
        'processes': processes,
    }
    return render(request, 'hr_admin/set_override_process.html', context)


# ============================================================
# STAFF MANAGEMENT
# ============================================================

from accounts.models import CustomUser
from departments.models import Department
from branches.models import Branch
from appraisals.models import Appraisal, AppraisalCycle
from .forms import StaffForm, DepartmentForm
from django.db.models import Count, Avg, F, Q


@hr_required
def staff_list(request):
    selected_branch_id = request.GET.get('branch') or ''
    selected_department_id = request.GET.get('department') or ''
    selected_cycle_id = request.GET.get('cycle') or ''
    selected_status = request.GET.get('status') or ''
    selected_role = request.GET.get('role') or ''
    search_q = (request.GET.get('q') or '').strip()

    branches = Branch.objects.all()
    departments = Department.objects.all()
    cycles = AppraisalCycle.objects.select_related('branch').all()

    selected_cycle = None
    if selected_cycle_id:
        selected_cycle = cycles.filter(pk=selected_cycle_id).first()
    if selected_cycle is None:
        selected_cycle = cycles.filter(status=AppraisalCycle.ACTIVE).first()
        selected_cycle_id = str(selected_cycle.pk) if selected_cycle else ''

    staff = CustomUser.objects.all().select_related('department', 'supervisor').prefetch_related('branches')

    if selected_branch_id:
        staff = staff.filter(branches__id=selected_branch_id).distinct()
        departments = departments.filter(branches__id=selected_branch_id).distinct()

    if selected_department_id:
        staff = staff.filter(department_id=selected_department_id)

    if selected_role:
        staff = staff.filter(role=selected_role)

    if search_q:
        staff = staff.filter(
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q) |
            Q(username__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(staff_id__icontains=search_q) |
            Q(designation__icontains=search_q)
        )

    if selected_cycle and selected_status:
        cycle_appraisals = Appraisal.objects.filter(cycle=selected_cycle)
        if selected_status == 'NO_RECORD':
            staff = staff.exclude(appraisals__cycle=selected_cycle)
        else:
            staff = staff.filter(
                id__in=cycle_appraisals.filter(status=selected_status).values('staff_id')
            )

    staff = list(staff.order_by('last_name', 'first_name', 'username'))

    appraisal_map = {}
    if selected_cycle and staff:
        appraisal_map = {
            appraisal.staff_id: appraisal
            for appraisal in Appraisal.objects.filter(
                cycle=selected_cycle,
                staff_id__in=[person.id for person in staff],
            )
        }

    for person in staff:
        person.selected_cycle_appraisal = appraisal_map.get(person.id)

    context = {
        'staff': staff,
        'branches': branches,
        'departments': departments,
        'cycles': cycles,
        'role_choices': CustomUser.ROLE_CHOICES,
        'appraisal_status_choices': Appraisal.STATUS_CHOICES,
        'selected_branch_id': selected_branch_id,
        'selected_department_id': selected_department_id,
        'selected_cycle_id': selected_cycle_id,
        'selected_status': selected_status,
        'selected_role': selected_role,
        'search_q': search_q,
        'selected_cycle': selected_cycle,
    }
    return render(request, 'hr_admin/staff_list.html', context)


@hr_required
def staff_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member created successfully.')
            return redirect('hr_admin:staff_list')
    else:
        form = StaffForm()
    return render(request, 'hr_admin/staff_form.html', {'form': form, 'action': 'Create'})


@hr_required
def staff_edit(request, pk):
    staff = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member updated successfully.')
            return redirect('hr_admin:staff_list')
    else:
        form = StaffForm(instance=staff)
    return render(request, 'hr_admin/staff_form.html', {'form': form, 'action': 'Edit'})


# ============================================================
# DEPARTMENT MANAGEMENT
# ============================================================

@hr_required
def department_list(request):
    departments = Department.objects.all().select_related('hod')
    return render(request, 'hr_admin/department_list.html', {'departments': departments})


@hr_required
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department created successfully.')
            return redirect('hr_admin:department_list')
    else:
        form = DepartmentForm()
    return render(request, 'hr_admin/department_form.html', {'form': form, 'action': 'Create'})


@hr_required
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully.')
            return redirect('hr_admin:department_list')
    else:
        form = DepartmentForm(instance=department)
    return render(request, 'hr_admin/department_form.html', {'form': form, 'action': 'Edit'})


# ============================================================
# REPORTS & ANALYTICS
# ============================================================

@hr_required
def reports_dashboard(request):
    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()

    total_staff = CustomUser.objects.exclude(role='HR_ADMIN').count()
    appraisal_stats = {}

    if active_cycle:
        appraisals = active_cycle.appraisals.all()
        appraisal_stats = {
            'total': appraisals.count(),
            'not_started': appraisals.filter(status='NOT_STARTED').count(),
            'draft': appraisals.filter(status='DRAFT').count(),
            'submitted': appraisals.filter(status='SUBMITTED').count(),
            'in_review': appraisals.filter(status='AWAITING_STEP_REVIEW').count(),
            'approved': appraisals.filter(status='APPROVED').count(),
            'acknowledged': appraisals.filter(status='STAFF_ACKNOWLEDGED').count(),
        }

    return render(request, 'hr_admin/reports.html', {
        'active_cycle': active_cycle,
        'total_staff': total_staff,
        'appraisal_stats': appraisal_stats
    })


# ============================================================
# CYCLE SETTINGS
# ============================================================

def _initialize_cycle_appraisals(cycle):
    """
    Create Appraisal records + AppraisalApprovalAssignment records
    for all targeted staff when a cycle is activated.
    """
    base_active_staff = CustomUser.objects.filter(
        is_active=True,
        role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.DIRECTORATE]
    )

    target_depts = cycle.target_departments.all()
    target_users = cycle.target_staff.all()

    if target_depts.exists() or target_users.exists():
        active_staff = CustomUser.objects.none()
        if target_depts.exists():
            active_staff = active_staff | base_active_staff.filter(department__in=target_depts)
        if target_users.exists():
            active_staff = active_staff | base_active_staff.filter(
                id__in=target_users.values_list('id', flat=True)
            )
        active_staff = active_staff.distinct()
    else:
        active_staff = base_active_staff

    excluded_ids = set(cycle.excluded_staff.values_list('id', flat=True))
    active_staff = active_staff.exclude(id__in=excluded_ids)

    general_process = cycle.general_approval_process

    for staff in active_staff:
        appraisal, created = Appraisal.objects.get_or_create(
            cycle=cycle,
            staff=staff,
            defaults={
                'status': Appraisal.NOT_STARTED,
                'supervisor': staff.supervisor,
            }
        )

        if created:
            # Initialize narrative, KPI, competency records
            for field in cycle.narrative_fields.all():
                NarrativeResponse.objects.get_or_create(appraisal=appraisal, field=field)
            for item in KPIItem.objects.filter(category__cycle=cycle):
                KPIScore.objects.get_or_create(appraisal=appraisal, kpi_item=item)
            for item in CompetencyItem.objects.filter(category__cycle=cycle):
                CompetencyScore.objects.get_or_create(appraisal=appraisal, competency_item=item)

        # Initialize approval assignments for general process
        if general_process:
            _create_assignments_for_appraisal(appraisal, general_process)


def _create_assignments_for_appraisal(appraisal, process):
    """Create AppraisalApprovalAssignment records for each step in the process."""
    for step in process.steps.all():
        assignment, created = AppraisalApprovalAssignment.objects.get_or_create(
            appraisal=appraisal,
            step=step,
        )
        # Auto-assign step 1 to the staff's supervisor
        if created and step.step_number == 1 and appraisal.staff.supervisor:
            assignment.approver = appraisal.staff.supervisor
            assignment.save()


def _sync_assignments_for_process(cycle, process):
    """Sync assignment records for all appraisals in a newly saved general process."""
    for appraisal in cycle.appraisals.all():
        if not appraisal.override_process:
            _create_assignments_for_appraisal(appraisal, process)


def sync_active_cycle_appraisals(cycle):
    """Sync appraisals and assignments for an already-active cycle."""
    _initialize_cycle_appraisals(cycle)

    # Remove unintended appraisals that haven't started
    base_active_staff = CustomUser.objects.filter(
        is_active=True,
        role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.DIRECTORATE]
    )
    target_depts = cycle.target_departments.all()
    target_users = cycle.target_staff.all()

    if target_depts.exists() or target_users.exists():
        intended = CustomUser.objects.none()
        if target_depts.exists():
            intended = intended | base_active_staff.filter(department__in=target_depts)
        if target_users.exists():
            intended = intended | base_active_staff.filter(id__in=target_users.values_list('id', flat=True))
        intended = intended.distinct()
    else:
        intended = base_active_staff

    excluded_ids = set(cycle.excluded_staff.values_list('id', flat=True))
    intended_ids = set(intended.exclude(id__in=excluded_ids).values_list('id', flat=True))

    for appraisal in Appraisal.objects.filter(cycle=cycle):
        if appraisal.staff_id not in intended_ids:
            if appraisal.status == Appraisal.NOT_STARTED:
                appraisal.delete()


@hr_required
def cycle_settings(request, pk):
    from branches.models import Branch
    cycle = get_object_or_404(AppraisalCycle, pk=pk)

    if request.method == 'POST':
        cycle.name = request.POST.get('name')

        start_date = request.POST.get('start_date')
        if start_date:
            cycle.start_date = start_date

        end_date = request.POST.get('end_date')
        if end_date:
            cycle.end_date = end_date

        cycle.scoring_scale = request.POST.get('scoring_scale', 5)

        branch_id = request.POST.get('branch')
        if branch_id:
            cycle.branch = get_object_or_404(Branch, pk=branch_id)

        cycle.save()

        target_depts = request.POST.getlist('target_departments')
        cycle.target_departments.set(target_depts)

        target_users = request.POST.getlist('target_staff')
        cycle.target_staff.set(target_users)

        if not target_depts and not target_users and cycle.branch:
            branch_members = cycle.branch.members.filter(
                is_active=True,
                role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.DIRECTORATE]
            )
            cycle.target_staff.set(branch_members)

        if target_users:
            cycle.excluded_staff.remove(*target_users)

        if cycle.status == AppraisalCycle.ACTIVE:
            sync_active_cycle_appraisals(cycle)

        messages.success(request, f"Settings for '{cycle.name}' updated successfully.")
        return redirect('hr_admin:cycle_settings', pk=cycle.pk)

    from departments.models import Department

    context = {
        'cycle': cycle,
        'action': 'Edit Settings for',
        'branches': Branch.objects.all(),
        'departments': Department.objects.all(),
        'staff': CustomUser.objects.filter(
            is_active=True,
            role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.DIRECTORATE]
        ),
        'target_dept_ids': cycle.target_departments.values_list('id', flat=True),
        'target_staff_ids': cycle.target_staff.values_list('id', flat=True),
        'excluded_staff': cycle.excluded_staff.all()
    }

    if cycle.status == AppraisalCycle.ACTIVE:
        context['participants'] = cycle.appraisals.select_related('staff', 'staff__department').all()
    else:
        base_active = CustomUser.objects.filter(
            is_active=True,
            role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.DIRECTORATE]
        )
        if cycle.target_departments.exists() or cycle.target_staff.exists():
            intended = CustomUser.objects.none()
            if cycle.target_departments.exists():
                intended = intended | base_active.filter(department__in=cycle.target_departments.all())
            if cycle.target_staff.exists():
                intended = intended | base_active.filter(id__in=cycle.target_staff.values_list('id', flat=True))
            context['intended_staff'] = intended.distinct().select_related('department')
        else:
            context['intended_staff'] = base_active.select_related('department')

    return render(request, 'hr_admin/cycle_form.html', context)


@hr_required
def remove_appraisal(request, pk):
    appraisal = get_object_or_404(Appraisal, pk=pk)
    cycle_pk = appraisal.cycle.pk
    staff_name = appraisal.staff.full_name

    if request.method == 'POST':
        if appraisal.status == Appraisal.NOT_STARTED:
            appraisal.cycle.excluded_staff.add(appraisal.staff)
            appraisal.cycle.target_staff.remove(appraisal.staff)
            appraisal.delete()
            messages.success(request, f"Appraisal for {staff_name} removed successfully.")
        else:
            messages.error(request, f"Cannot remove {staff_name} — they have already started their appraisal.")

    return redirect('hr_admin:cycle_settings', pk=cycle_pk)


@hr_required
def readd_staff(request, cycle_pk, staff_id):
    cycle = get_object_or_404(AppraisalCycle, pk=cycle_pk)
    staff = get_object_or_404(CustomUser, pk=staff_id)

    if request.method == 'POST':
        cycle.excluded_staff.remove(staff)
        cycle.target_staff.add(staff)
        if cycle.status == AppraisalCycle.ACTIVE:
            sync_active_cycle_appraisals(cycle)
        messages.success(request, f"{staff.full_name} has been re-added to the appraisal cycle.")

    return redirect('hr_admin:cycle_settings', pk=cycle_pk)


# ============================================================
# BRANCH MANAGEMENT
# ============================================================

@hr_required
def branch_list(request):
    from branches.models import Branch
    branches = Branch.objects.all()
    return render(request, 'hr_admin/branch_list.html', {'branches': branches})


@hr_required
def branch_create(request):
    from branches.models import Branch
    from departments.models import Department

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()

        if not name or not code:
            messages.error(request, "Branch name and code are required.")
            return redirect('hr_admin:branch_create')

        branch = Branch.objects.create(name=name, code=code, description=description)

        dept_ids = request.POST.getlist('departments')
        branch.departments.set(dept_ids)

        member_ids = request.POST.getlist('members')
        branch.members.set(member_ids)

        messages.success(request, f"Branch '{branch.name}' created successfully.")
        return redirect('hr_admin:branch_list')

    context = {
        'action': 'Create',
        'departments': Department.objects.all(),
        'staff': CustomUser.objects.filter(is_active=True),
    }
    return render(request, 'hr_admin/branch_form.html', context)


@hr_required
def branch_edit(request, pk):
    from branches.models import Branch
    from departments.models import Department

    branch = get_object_or_404(Branch, pk=pk)

    if request.method == 'POST':
        branch.name = request.POST.get('name', '').strip()
        branch.code = request.POST.get('code', '').strip()
        branch.description = request.POST.get('description', '').strip()
        branch.save()

        dept_ids = request.POST.getlist('departments')
        branch.departments.set(dept_ids)

        member_ids = request.POST.getlist('members')
        branch.members.set(member_ids)

        messages.success(request, f"Branch '{branch.name}' updated successfully.")
        return redirect('hr_admin:branch_list')

    context = {
        'action': 'Edit',
        'branch': branch,
        'departments': Department.objects.all(),
        'staff': CustomUser.objects.filter(is_active=True),
        'selected_dept_ids': list(branch.departments.values_list('id', flat=True)),
        'selected_member_ids': list(branch.members.values_list('id', flat=True)),
    }
    return render(request, 'hr_admin/branch_form.html', context)


@hr_required
def branch_delete(request, pk):
    from branches.models import Branch
    branch = get_object_or_404(Branch, pk=pk)

    if request.method == 'POST':
        if branch.cycles.exists():
            messages.error(request, f"Cannot delete '{branch.name}' — it is linked to appraisal cycles.")
        else:
            name = branch.name
            branch.delete()
            messages.success(request, f"Branch '{name}' deleted.")

    return redirect('hr_admin:branch_list')


@hr_required
def api_branch_data(request, branch_pk):
    """Return JSON of departments and staff belonging to a specific branch."""
    from branches.models import Branch
    branch = get_object_or_404(Branch, pk=branch_pk)

    departments = list(branch.departments.values('id', 'name', 'code'))
    members = list(branch.members.filter(is_active=True).values(
        'id', 'first_name', 'last_name', 'role', 'department__name'
    ))

    # Build a display-friendly list
    staff_list = []
    for m in members:
        full_name = f"{m['first_name']} {m['last_name']}".strip() or f"User #{m['id']}"
        role_map = {
            'STAFF': 'Staff', 'SUPERVISOR': 'Supervisor', 'HOD': 'Head of Department',
            'DIRECTORATE': 'Director/Executive', 'HR_ADMIN': 'HR Administrator',
        }
        staff_list.append({
            'id': m['id'],
            'full_name': full_name,
            'role': m['role'],
            'role_display': role_map.get(m['role'], m['role']),
            'department': m['department__name'] or '—',
        })

    return JsonResponse({
        'departments': departments,
        'staff': staff_list,
    })
