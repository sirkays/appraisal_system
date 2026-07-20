from appraisals.models import AppraisalCycle


def active_cycles(request):
    """
    Injects all active appraisal cycles and the currently selected one
    into every template context.

    The selected cycle is stored in request.session['selected_cycle_id'].
    If no cycle is explicitly selected, the most recent active cycle is used.
    """
    if not request.user.is_authenticated:
        return {}

    cycles = list(
        AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE)
        .order_by('-start_date')
    )

    if not cycles:
        return {
            'all_active_cycles': [],
            'selected_cycle': None,
        }

    selected_id = request.session.get('selected_cycle_id')
    selected_cycle = None

    if selected_id:
        selected_cycle = next((c for c in cycles if c.id == selected_id), None)

    # Fallback: pick the most recent active cycle
    if not selected_cycle:
        selected_cycle = cycles[0]
        request.session['selected_cycle_id'] = selected_cycle.id

    return {
        'all_active_cycles': cycles,
        'selected_cycle': selected_cycle,
    }
