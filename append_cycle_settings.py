append_str = """
def sync_active_cycle_appraisals(cycle):
    from accounts.models import CustomUser
    from appraisals.models import Appraisal, NarrativeResponse, KPIScore, CompetencyScore, KPIItem, CompetencyItem
    
    # 1. Determine intended audience based on current targeting
    base_active_staff = CustomUser.objects.filter(is_active=True, role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD])
    target_depts = cycle.target_departments.all()
    target_users = cycle.target_staff.all()
    
    if target_depts.exists() or target_users.exists():
        intended_staff = CustomUser.objects.none()
        if target_depts.exists():
            intended_staff = intended_staff | base_active_staff.filter(department__in=target_depts)
        if target_users.exists():
            intended_staff = intended_staff | base_active_staff.filter(id__in=target_users.values_list('id', flat=True))
        intended_staff = intended_staff.distinct()
    else:
        intended_staff = base_active_staff
        
    intended_staff_ids = set(intended_staff.values_list('id', flat=True))
    
    # 2. Add missing appraisals
    for staff in intended_staff:
        appraisal, created = Appraisal.objects.get_or_create(
            cycle=cycle,
            staff=staff,
            defaults={
                'status': Appraisal.NOT_STARTED,
                'supervisor': staff.supervisor
            }
        )
        if created:
            # Initialize Narrative Responses
            for field in cycle.narrative_fields.all():
                NarrativeResponse.objects.get_or_create(appraisal=appraisal, field=field)
                
            # Initialize KPI Scores
            for item in KPIItem.objects.filter(category__cycle=cycle):
                KPIScore.objects.get_or_create(appraisal=appraisal, kpi_item=item)
                
            # Initialize Competency Scores
            for item in CompetencyItem.objects.filter(category__cycle=cycle):
                CompetencyScore.objects.get_or_create(appraisal=appraisal, competency_item=item)
                
    # 3. Remove unintended appraisals ONLY IF they haven't started
    existing_appraisals = Appraisal.objects.filter(cycle=cycle)
    for appraisal in existing_appraisals:
        if appraisal.staff_id not in intended_staff_ids:
            if appraisal.status == Appraisal.NOT_STARTED:
                appraisal.delete()

@login_required
def cycle_settings(request, pk):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
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
        cycle.save()
        
        target_depts = request.POST.getlist('target_departments')
        cycle.target_departments.set(target_depts)
            
        target_users = request.POST.getlist('target_staff')
        cycle.target_staff.set(target_users)
        
        # If cycle is ACTIVE, sync the appraisals immediately
        if cycle.status == AppraisalCycle.ACTIVE:
            sync_active_cycle_appraisals(cycle)
            
        messages.success(request, f"Settings for '{cycle.name}' updated successfully.")
        return redirect('hr_admin:cycle_list')
        
    from departments.models import Department
    from accounts.models import CustomUser
    
    context = {
        'cycle': cycle,
        'action': 'Edit Settings for',
        'departments': Department.objects.all(),
        'staff': CustomUser.objects.filter(is_active=True, role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD])
    }
    return render(request, 'hr_admin/cycle_form.html', context)
"""

with open('c:\\Users\\sirkays\\Desktop\\workspace\\appriasal_system\\hr_admin\\views.py', 'a', encoding='utf-8') as f:
    f.write(append_str)
