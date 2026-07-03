from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from appraisals.models import AppraisalCycle, KPICategory, CompetencyCategory, NarrativeField
import json

@login_required
def dashboard(request):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    from django.contrib.auth import get_user_model
    User = get_user_model()
    context = {
        'active_cycle_count': AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).count(),
        'total_staff': User.objects.count(),
    }
    return render(request, 'hr_admin/dashboard.html', context)

@login_required
def cycle_list(request):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    cycles = AppraisalCycle.objects.all().order_by('-created_at')
    return render(request, 'hr_admin/cycle_list.html', {'cycles': cycles})

@login_required
def cycle_create(request):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    if request.method == 'POST':
        # Create cycle and redirect to edit/builder mode
        name = request.POST.get('name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        scoring_scale = request.POST.get('scoring_scale', 5)
        
        cycle = AppraisalCycle.objects.create(
            name=name,
            start_date=start_date,
            end_date=end_date,
            scoring_scale=scoring_scale,
            status=AppraisalCycle.DRAFT
        )
        
        target_depts = request.POST.getlist('target_departments')
        if target_depts:
            cycle.target_departments.set(target_depts)
            
        target_users = request.POST.getlist('target_staff')
        if target_users:
            cycle.target_staff.set(target_users)
            
        if not target_depts and not target_users:
            from accounts.models import CustomUser
            all_active_users = CustomUser.objects.filter(is_active=True, role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD])
            cycle.target_staff.set(all_active_users)
            
        messages.success(request, f"Cycle '{cycle.name}' created. Now configure the fields.")
        return redirect('hr_admin:cycle_edit', pk=cycle.pk)
        
    from departments.models import Department
    from accounts.models import CustomUser
    
    context = {
        'departments': Department.objects.all(),
        'staff': CustomUser.objects.filter(is_active=True, role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD]),
        'target_dept_ids': [],
        'target_staff_ids': []
    }
    return render(request, 'hr_admin/cycle_form.html', context)

@login_required
def cycle_detail(request, pk):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    cycle = get_object_or_404(AppraisalCycle, pk=pk)
    return render(request, 'hr_admin/cycle_detail.html', {'cycle': cycle})

@login_required
def cycle_edit(request, pk):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    cycle = get_object_or_404(AppraisalCycle, pk=pk)
    
    if request.method == 'POST':
        # Handles AJAX JSON submissions from the builder
        try:
            data = json.loads(request.body)
            
            cycle.name = data.get('name', cycle.name)
            if data.get('start_date'):
                cycle.start_date = data.get('start_date')
            if data.get('end_date'):
                cycle.end_date = data.get('end_date')
            cycle.scoring_scale = data.get('scoring_scale', cycle.scoring_scale)
            cycle.status = data.get('status', cycle.status)
            cycle.save()
            
            # Sync Narrative Fields
            from appraisals.models import NarrativeField, KPICategory, KPIItem, CompetencyCategory, CompetencyItem
            
            for nf_data in data.get('narrative_fields', []):
                if nf_data.get('deleted') and nf_data.get('id'):
                    NarrativeField.objects.filter(id=nf_data['id']).delete()
                elif not nf_data.get('deleted'):
                    NarrativeField.objects.update_or_create(
                        id=nf_data.get('id'),
                        defaults={
                            'cycle': cycle,
                            'name': nf_data.get('name'),
                            'is_supervisor_field': nf_data.get('is_supervisor_field', False),
                            'order': nf_data.get('order', 0)
                        }
                    )
            
            # Sync KPI Categories and Items
            for cat_data in data.get('kpi_categories', []):
                if cat_data.get('deleted') and cat_data.get('id'):
                    KPICategory.objects.filter(id=cat_data['id']).delete()
                elif not cat_data.get('deleted'):
                    cat, _ = KPICategory.objects.update_or_create(
                        id=cat_data.get('id'),
                        defaults={
                            'cycle': cycle,
                            'name': cat_data.get('name'),
                            'weight': cat_data.get('weight', 0),
                            'order': cat_data.get('order', 0)
                        }
                    )
                    
                    for item_data in cat_data.get('items', []):
                        if item_data.get('deleted') and item_data.get('id'):
                            KPIItem.objects.filter(id=item_data['id']).delete()
                        elif not item_data.get('deleted'):
                            KPIItem.objects.update_or_create(
                                id=item_data.get('id'),
                                defaults={
                                    'category': cat,
                                    'name': item_data.get('name'),
                                    'weight': item_data.get('weight', 0),
                                    'order': item_data.get('order', 0)
                                }
                            )
                            
            # Sync Competency Categories and Items
            for cat_data in data.get('competency_categories', []):
                if cat_data.get('deleted') and cat_data.get('id'):
                    CompetencyCategory.objects.filter(id=cat_data['id']).delete()
                elif not cat_data.get('deleted'):
                    cat, _ = CompetencyCategory.objects.update_or_create(
                        id=cat_data.get('id'),
                        defaults={
                            'cycle': cycle,
                            'name': cat_data.get('name'),
                            'weight': cat_data.get('weight', 0),
                            'order': cat_data.get('order', 0)
                        }
                    )
                    
                    for item_data in cat_data.get('items', []):
                        if item_data.get('deleted') and item_data.get('id'):
                            CompetencyItem.objects.filter(id=item_data['id']).delete()
                        elif not item_data.get('deleted'):
                            CompetencyItem.objects.update_or_create(
                                id=item_data.get('id'),
                                defaults={
                                    'category': cat,
                                    'name': item_data.get('name'),
                                    'weight': item_data.get('weight', 0),
                                    'order': item_data.get('order', 0)
                                }
                            )
            
            # If cycle is being activated, bulk-create Appraisals
            if cycle.status == AppraisalCycle.ACTIVE:
                from accounts.models import CustomUser
                from appraisals.models import Appraisal, NarrativeResponse, KPIScore, CompetencyScore
                
                # Fetch all active staff based on cycle targeting
                base_active_staff = CustomUser.objects.filter(is_active=True, role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD])
                
                target_depts = cycle.target_departments.all()
                target_users = cycle.target_staff.all()
                
                if target_depts.exists() or target_users.exists():
                    active_staff = CustomUser.objects.none()
                    if target_depts.exists():
                        active_staff = active_staff | base_active_staff.filter(department__in=target_depts)
                    if target_users.exists():
                        active_staff = active_staff | base_active_staff.filter(id__in=target_users.values_list('id', flat=True))
                    active_staff = active_staff.distinct()
                else:
                    active_staff = base_active_staff
                
                for staff in active_staff:
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
                        narrative_fields = cycle.narrative_fields.all()
                        for field in narrative_fields:
                            NarrativeResponse.objects.get_or_create(appraisal=appraisal, field=field)
                            
                        # Initialize KPI Scores
                        kpi_items = KPIItem.objects.filter(category__cycle=cycle)
                        for item in kpi_items:
                            KPIScore.objects.get_or_create(appraisal=appraisal, kpi_item=item)
                            
                        # Initialize Competency Scores
                        comp_items = CompetencyItem.objects.filter(category__cycle=cycle)
                        for item in comp_items:
                            CompetencyScore.objects.get_or_create(appraisal=appraisal, competency_item=item)
            
            return JsonResponse({"status": "success", "message": "Cycle saved successfully."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return render(request, 'hr_admin/cycle_builder.html', {'cycle': cycle})


# --- Staff Management ---
from accounts.models import CustomUser
from departments.models import Department
from .forms import StaffForm, DepartmentForm
from django.db.models import Count, Avg, F, Q

@login_required
def staff_list(request):
    if request.user.role != 'HR_ADMIN':
        return redirect('accounts:dashboard_redirect')
    
    staff = CustomUser.objects.all().select_related('department', 'supervisor')
    return render(request, 'hr_admin/staff_list.html', {'staff': staff})

@login_required
def staff_create(request):
    if request.user.role != 'HR_ADMIN':
        return redirect('accounts:dashboard_redirect')
        
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member created successfully.')
            return redirect('hr_admin:staff_list')
    else:
        form = StaffForm()
        
    return render(request, 'hr_admin/staff_form.html', {'form': form, 'action': 'Create'})

@login_required
def staff_edit(request, pk):
    if request.user.role != 'HR_ADMIN':
        return redirect('accounts:dashboard_redirect')
        
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

# --- Department Management ---

@login_required
def department_list(request):
    if request.user.role != 'HR_ADMIN':
        return redirect('accounts:dashboard_redirect')
        
    departments = Department.objects.all().select_related('hod')
    return render(request, 'hr_admin/department_list.html', {'departments': departments})

@login_required
def department_create(request):
    if request.user.role != 'HR_ADMIN':
        return redirect('accounts:dashboard_redirect')
        
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department created successfully.')
            return redirect('hr_admin:department_list')
    else:
        form = DepartmentForm()
        
    return render(request, 'hr_admin/department_form.html', {'form': form, 'action': 'Create'})

@login_required
def department_edit(request, pk):
    if request.user.role != 'HR_ADMIN':
        return redirect('accounts:dashboard_redirect')
        
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

# --- Reports & Analytics ---

@login_required
def reports_dashboard(request):
    if request.user.role != 'HR_ADMIN':
        return redirect('accounts:dashboard_redirect')
        
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
            'under_review': appraisals.filter(status='UNDER_REVIEW').count(),
            'reviewed': appraisals.filter(status='REVIEWED').count(),
            'approved': appraisals.filter(status='APPROVED').count(),
        }
        
    return render(request, 'hr_admin/reports.html', {
        'active_cycle': active_cycle,
        'total_staff': total_staff,
        'appraisal_stats': appraisal_stats
    })

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
        
    # Exclude specifically removed staff
    excluded_ids = set(cycle.excluded_staff.values_list('id', flat=True))
    intended_staff = intended_staff.exclude(id__in=excluded_ids)
        
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
        
        if not target_depts and not target_users:
            from accounts.models import CustomUser
            all_active_users = CustomUser.objects.filter(is_active=True, role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD])
            cycle.target_staff.set(all_active_users)
        
        # Remove targeted users from excluded_staff
        if target_users:
            cycle.excluded_staff.remove(*target_users)
        
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
        'staff': CustomUser.objects.filter(is_active=True, role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD]),
        'target_dept_ids': cycle.target_departments.values_list('id', flat=True),
        'target_staff_ids': cycle.target_staff.values_list('id', flat=True),
        'excluded_staff': cycle.excluded_staff.all()
    }
    
    # If cycle is active, pass the actual appraisals. If draft, pass intended staff.
    if cycle.status == AppraisalCycle.ACTIVE:
        context['participants'] = cycle.appraisals.select_related('staff', 'staff__department').all()
    else:
        # Calculate intended staff
        base_active = CustomUser.objects.filter(is_active=True, role__in=[CustomUser.STAFF, CustomUser.SUPERVISOR, CustomUser.HOD])
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

@login_required
def remove_appraisal(request, pk):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    from appraisals.models import Appraisal
    appraisal = get_object_or_404(Appraisal, pk=pk)
    cycle_pk = appraisal.cycle.pk
    staff_name = appraisal.staff.full_name
    
    if request.method == 'POST':
        if appraisal.status == Appraisal.NOT_STARTED:
            # Add to excluded_staff so they aren't recreated on sync
            appraisal.cycle.excluded_staff.add(appraisal.staff)
            # Remove from target_staff if they were explicitly targeted
            appraisal.cycle.target_staff.remove(appraisal.staff)
            appraisal.delete()
            messages.success(request, f"Appraisal for {staff_name} removed successfully.")
        else:
            messages.error(request, f"Cannot remove {staff_name} because they have already started their appraisal.")
            
    return redirect('hr_admin:cycle_settings', pk=cycle_pk)

@login_required
def readd_staff(request, cycle_pk, staff_id):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    cycle = get_object_or_404(AppraisalCycle, pk=cycle_pk)
    from accounts.models import CustomUser
    staff = get_object_or_404(CustomUser, pk=staff_id)
    
    if request.method == 'POST':
        cycle.excluded_staff.remove(staff)
        cycle.target_staff.add(staff)
        if cycle.status == AppraisalCycle.ACTIVE:
            sync_active_cycle_appraisals(cycle)
        messages.success(request, f"{staff.full_name} has been re-added to the appraisal cycle.")
        
    return redirect('hr_admin:cycle_settings', pk=cycle_pk)
