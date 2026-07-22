from appraisals.models import AppraisalCycle


def active_cycles(request):
    """
    Injects only the active appraisal cycles that the current user is
    eligible to participate in, plus the currently selected one.

    The selected cycle is stored in request.session['selected_cycle_id'].
    If no cycle is explicitly selected, the most recent eligible cycle is used.

    Eligibility is determined by AppraisalCycle.get_eligible_staff():
      - If the cycle targets specific departments or staff, only those users see it.
      - If neither targeting field is set, all branch-matched (or all) active staff see it.
      - Excluded staff never see the cycle.

    HR admins (staff with is_staff or HR_ADMIN role) bypass the eligibility
    filter so they can manage all active cycles.
    """
    if not request.user.is_authenticated:
        return {}

    from accounts.models import CustomUser

    all_active = list(
        AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE)
        .order_by('-start_date')
        .prefetch_related('target_departments', 'target_staff', 'excluded_staff')
    )

    # HR admins see everything; regular users only see cycles they're eligible for
    if request.user.role == CustomUser.HR_ADMIN or request.user.is_staff:
        cycles = all_active
    else:
        cycles = [c for c in all_active if request.user in c.get_eligible_staff()]

    if not cycles:
        return {
            'all_active_cycles': [],
            'selected_cycle': None,
        }

    selected_id = request.session.get('selected_cycle_id')
    selected_cycle = None

    if selected_id:
        selected_cycle = next((c for c in cycles if c.id == selected_id), None)

    # Fallback: pick the most recent eligible active cycle
    if not selected_cycle:
        selected_cycle = cycles[0]
        request.session['selected_cycle_id'] = selected_cycle.id

    return {
        'all_active_cycles': cycles,
        'selected_cycle': selected_cycle,
    }
