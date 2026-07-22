from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth import logout as django_logout
from django.contrib import messages
from accounts.models import CustomUser
from appraisals.models import AppraisalCycle, Appraisal, KPIItem, CompetencyItem, AppraisalApprovalAssignment


class LoginView(DjangoLoginView):
    """Custom LoginView referencing the styled login template."""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return _role_dashboard_url(self.request.user)


def _role_dashboard_url(user):
    """Return the dashboard URL for a given user's role."""
    from django.urls import reverse
    role_map = {
        CustomUser.HR_ADMIN: 'hr_admin:dashboard',
        CustomUser.HOD: 'accounts:hod_dashboard',
        CustomUser.SUPERVISOR: 'accounts:supervisor_dashboard',
        CustomUser.DIRECTORATE: 'accounts:directorate_dashboard',
    }
    name = role_map.get(user.role)
    if name:
        return reverse(name)
    return reverse('accounts:staff_dashboard')


@login_required
def dashboard_redirect(request):
    """Redirects users to their appropriate dashboard based on their role."""
    return redirect(_role_dashboard_url(request.user))


def logout_view(request):
    """Logs out the user and redirects to the login page."""
    django_logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('accounts:login')


@login_required
def switch_cycle(request):
    """Store the selected cycle ID in the session and redirect back.

    Only accept the switch if the requesting user is eligible to participate
    in the chosen cycle (or is an HR admin who manages all cycles).
    """
    if request.method == 'POST':
        cycle_id = request.POST.get('cycle_id')
        if cycle_id:
            try:
                cycle = AppraisalCycle.objects.get(pk=int(cycle_id), status=AppraisalCycle.ACTIVE)
                # Verify the user is allowed to see/switch to this cycle
                if request.user.role == CustomUser.HR_ADMIN or request.user.is_staff \
                        or request.user in cycle.get_eligible_staff():
                    request.session['selected_cycle_id'] = cycle.id
            except (ValueError, AppraisalCycle.DoesNotExist):
                pass
    return redirect(_role_dashboard_url(request.user))


# ============================================================
# HELPERS
# ============================================================

def _get_eligible_cycles_for_user(user):
    """
    Return a list of active AppraisalCycle objects the given user is eligible
    to participate in.  HR admins see all active cycles.
    """
    qs = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).order_by('-start_date')
    if user.role == CustomUser.HR_ADMIN or user.is_staff:
        return list(qs)
    return [c for c in qs if user in c.get_eligible_staff()]


def _get_selected_cycle(request):
    """
    Return the session-selected active cycle, or fall back to the most recent
    cycle the user is eligible for.
    """
    eligible = _get_eligible_cycles_for_user(request.user)
    if not eligible:
        return None

    selected_id = request.session.get('selected_cycle_id')
    if selected_id:
        match = next((c for c in eligible if c.id == selected_id), None)
        if match:
            return match
        # Session points to a cycle the user is no longer eligible for — reset it
        request.session.pop('selected_cycle_id', None)

    # Fallback: most recent eligible cycle
    return eligible[0]


# ============================================================
# STAFF DASHBOARD
# ============================================================

@login_required
def staff_dashboard(request):
    appraisal = None
    progress = 0
    status_display = "No Active Cycle"
    approval_steps = []
    current_step_label = None

    # Use the session-selected cycle (set by the global cycle selector)
    active_cycle = _get_selected_cycle(request)

    if active_cycle:
        appraisal = Appraisal.objects.filter(
            cycle=active_cycle, staff=request.user
        ).select_related('override_process').first()

        if appraisal:
            status_display = appraisal.get_status_display()

            # Always load process steps from the active process (general or override)
            process = appraisal.active_process
            if process:
                approval_steps = list(process.steps.all())

            if appraisal.status in [Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED, Appraisal.ARCHIVED]:
                progress = 100
            elif appraisal.status in [Appraisal.SUBMITTED, Appraisal.AWAITING_STEP_REVIEW]:
                if process:
                    total = process.steps.count()
                    done = appraisal.current_step_number - 1
                    progress = int((done / total) * 100) if total > 0 else 50
                    current_assignment = appraisal.current_assignment
                    if current_assignment:
                        current_step_label = current_assignment.step.label
                else:
                    progress = 50
            else:
                kpis_count = KPIItem.objects.filter(category__cycle=active_cycle).count()
                comps_count = CompetencyItem.objects.filter(category__cycle=active_cycle).count()
                total_items = kpis_count + comps_count

                scored_kpis = appraisal.kpi_scores.filter(self_score__isnull=False).count() if appraisal else 0
                scored_comps = appraisal.competency_scores.filter(self_score__isnull=False).count() if appraisal else 0
                scored_items = scored_kpis + scored_comps

                progress = int((scored_items / total_items) * 100) if total_items > 0 else 0
        else:
            status_display = "Not Started"
            process = active_cycle.general_approval_process
            if process:
                from hr_admin.views import _resolve_dynamic_approver
                is_valid = True
                for step in process.steps.all():
                    if not step.approver and not _resolve_dynamic_approver(request.user, step.role_required):
                        is_valid = False
                        break
                if is_valid:
                    approval_steps = list(process.steps.all())
            progress = 0

    # Past appraisals
    past_appraisals = Appraisal.objects.filter(
        staff=request.user
    ).select_related('cycle').order_by('-cycle__start_date')[:5]

    import datetime
    from django.utils import timezone
    days_remaining = None
    if active_cycle:
        try:
            today = timezone.localdate()
        except Exception:
            today = datetime.date.today()
        delta = active_cycle.end_date - today
        days_remaining = delta.days

    context = {
        'active_cycle': active_cycle,
        'appraisal': appraisal,
        'status_display': status_display,
        'progress': progress,
        'approval_steps': approval_steps,
        'current_step_label': current_step_label,
        'past_appraisals': past_appraisals,
        'days_remaining': days_remaining,
    }
    return render(request, 'accounts/dashboards/staff.html', context)


# ============================================================
# SUPERVISOR DASHBOARD
# ============================================================

@login_required
def supervisor_dashboard(request):
    if request.user.role != CustomUser.SUPERVISOR:
        return redirect('accounts:dashboard_redirect')

    active_cycle = _get_selected_cycle(request)

    context = {
        'active_cycle': active_cycle,
        'total_team': 0,
        'pending_self': 0,
        'awaiting_my_review': 0,
        'completed': 0,
        'pending_assignments': [],
        'past_actions': [],
    }

    if active_cycle:
        # Pending: appraisals where this user is the assigned approver for the current step
        pending_assignments = AppraisalApprovalAssignment.objects.filter(
            approver=request.user,
            status=AppraisalApprovalAssignment.PENDING,
            appraisal__cycle=active_cycle,
        ).select_related('appraisal__staff', 'step')

        # Filter to only current-step assignments (including appraisals returned to this step)
        ACTIONABLE_STATUSES = [
            Appraisal.SUBMITTED,
            Appraisal.AWAITING_STEP_REVIEW,
            Appraisal.RETURNED_TO_REVIEWER,
        ]
        current_pending = [
            a for a in pending_assignments
            if a.appraisal.current_step_number == a.step.step_number and
               a.appraisal.status in ACTIONABLE_STATUSES
        ]

        # Team (direct reports) stats
        team = CustomUser.objects.filter(supervisor=request.user)
        team_appraisals = Appraisal.objects.filter(staff__in=team, cycle=active_cycle).select_related('staff')

        pending_self = team_appraisals.filter(
            status__in=[Appraisal.NOT_STARTED, Appraisal.DRAFT, Appraisal.RETURNED_TO_STAFF]
        ).count()
        completed = team_appraisals.filter(
            status__in=[Appraisal.AWAITING_STEP_REVIEW, Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED]
        ).count()

        # Past review actions
        past_actions = AppraisalApprovalAssignment.objects.filter(
            approver=request.user,
            status__in=[AppraisalApprovalAssignment.APPROVED, AppraisalApprovalAssignment.RETURNED],
            appraisal__cycle=active_cycle,
        ).select_related('appraisal__staff', 'step').order_by('-actioned_at')[:5]

        context.update({
            'total_team': team.count(),
            'pending_self': pending_self,
            'awaiting_my_review': len(current_pending),
            'completed': completed,
            'pending_assignments': current_pending,
            'past_actions': past_actions,
        })

    return render(request, 'accounts/dashboards/supervisor.html', context)


# ============================================================
# HOD DASHBOARD
# ============================================================

@login_required
def hod_dashboard(request):
    if request.user.role != CustomUser.HOD:
        return redirect('accounts:dashboard_redirect')

    active_cycle = _get_selected_cycle(request)

    context = {
        'active_cycle': active_cycle,
        'total_dept_staff': 0,
        'awaiting_my_review': 0,
        'approved': 0,
        'pending_assignments': [],
        'dept_stats': [],
    }

    if active_cycle and request.user.department:
        dept_staff = CustomUser.objects.filter(department=request.user.department)
        dept_appraisals = Appraisal.objects.filter(
            staff__in=dept_staff, cycle=active_cycle
        ).select_related('staff')

        # Pending: my assignments as approver for current step
        pending_assignments = AppraisalApprovalAssignment.objects.filter(
            approver=request.user,
            status=AppraisalApprovalAssignment.PENDING,
            appraisal__cycle=active_cycle,
        ).select_related('appraisal__staff', 'step')

        ACTIONABLE_STATUSES = [
            Appraisal.SUBMITTED,
            Appraisal.AWAITING_STEP_REVIEW,
            Appraisal.RETURNED_TO_REVIEWER,
        ]
        current_pending = [
            a for a in pending_assignments
            if a.appraisal.current_step_number == a.step.step_number and
               a.appraisal.status in ACTIONABLE_STATUSES
        ]

        approved = dept_appraisals.filter(
            status__in=[Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED, Appraisal.ARCHIVED]
        ).count()

        context.update({
            'total_dept_staff': dept_staff.count(),
            'awaiting_my_review': len(current_pending),
            'approved': approved,
            'pending_assignments': current_pending,
            'dept_appraisals': dept_appraisals.order_by('staff__last_name'),
        })

    return render(request, 'accounts/dashboards/hod.html', context)


# ============================================================
# DIRECTORATE DASHBOARD
# ============================================================

@login_required
def directorate_dashboard(request):
    if request.user.role != CustomUser.DIRECTORATE:
        return redirect('accounts:dashboard_redirect')

    active_cycle = _get_selected_cycle(request)

    context = {
        'active_cycle': active_cycle,
        'total_staff': 0,
        'awaiting_my_review': 0,
        'approved_count': 0,
        'pending_assignments': [],
        'dept_summaries': [],
        'all_appraisals': [],
    }

    if active_cycle:
        from departments.models import Department

        # Director's pending review queue
        pending_assignments = AppraisalApprovalAssignment.objects.filter(
            approver=request.user,
            status=AppraisalApprovalAssignment.PENDING,
            appraisal__cycle=active_cycle,
        ).select_related('appraisal__staff', 'appraisal__staff__department', 'step')

        ACTIONABLE_STATUSES = [
            Appraisal.SUBMITTED,
            Appraisal.AWAITING_STEP_REVIEW,
            Appraisal.RETURNED_TO_REVIEWER,
        ]
        current_pending = [
            a for a in pending_assignments
            if a.appraisal.current_step_number == a.step.step_number and
               a.appraisal.status in ACTIONABLE_STATUSES
        ]

        # Org-wide statistics
        all_appraisals = active_cycle.appraisals.select_related('staff', 'staff__department')

        approved_count = all_appraisals.filter(
            status__in=[Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED]
        ).count()

        # Per-department summary
        departments = Department.objects.all()
        dept_summaries = []
        for dept in departments:
            dept_appraisals = all_appraisals.filter(staff__department=dept)
            total = dept_appraisals.count()
            if total == 0:
                continue
            dept_summaries.append({
                'department': dept,
                'total': total,
                'not_started': dept_appraisals.filter(status__in=['NOT_STARTED', 'DRAFT']).count(),
                'in_progress': dept_appraisals.filter(status__in=['SUBMITTED', 'AWAITING_STEP_REVIEW']).count(),
                'approved': dept_appraisals.filter(status__in=['APPROVED', 'STAFF_ACKNOWLEDGED']).count(),
                'completion_pct': int(
                    dept_appraisals.filter(
                        status__in=['APPROVED', 'STAFF_ACKNOWLEDGED']
                    ).count() / total * 100
                ) if total > 0 else 0,
            })

        context.update({
            'total_staff': all_appraisals.count(),
            'awaiting_my_review': len(current_pending),
            'approved_count': approved_count,
            'pending_assignments': current_pending,
            'dept_summaries': dept_summaries,
            'all_appraisals': all_appraisals.order_by('staff__last_name')[:50],
            'completion_pct': int(approved_count / all_appraisals.count() * 100) if all_appraisals.count() > 0 else 0,
        })

    return render(request, 'accounts/dashboards/directorate.html', context)


@login_required
def admin_dashboard(request):
    if request.user.role == CustomUser.HR_ADMIN:
        return redirect('hr_admin:dashboard')
    return redirect('accounts:dashboard_redirect')


# ============================================================
# PROFILE & SETTINGS
# ============================================================

@login_required
def profile(request):
    """
    My Profile — lets every user view and update their own basic info:
    first_name, last_name, email, phone, designation, profile picture,
    and change password.
    """
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        if action == 'change_password':
            from django.contrib.auth import update_session_auth_hash
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not user.check_password(current_password):
                messages.error(request, 'Your current password is incorrect.')
            elif len(new_password) < 8:
                messages.error(request, 'New password must be at least 8 characters.')
            elif new_password != confirm_password:
                messages.error(request, 'New password and confirmation do not match.')
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully.')
            return redirect('accounts:profile')
        else:
            user.first_name = request.POST.get('first_name', user.first_name).strip()
            user.last_name = request.POST.get('last_name', user.last_name).strip()
            user.email = request.POST.get('email', user.email).strip()
            user.phone = request.POST.get('phone', user.phone).strip()
            user.designation = request.POST.get('designation', user.designation).strip()

            if 'profile_picture' in request.FILES:
                user.profile_picture = request.FILES['profile_picture']

            user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {'profile_user': user})


@login_required
def settings(request):
    """
    Settings — password change only. Validates current password before
    updating to prevent unauthorised changes.
    """
    from django.contrib.auth import update_session_auth_hash

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(current_password):
            messages.error(request, 'Your current password is incorrect.')
        elif len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters.')
        elif new_password != confirm_password:
            messages.error(request, 'New password and confirmation do not match.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            # Keep the user logged in after password change
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully.')
            return redirect('accounts:settings')

    return render(request, 'accounts/settings.html')
