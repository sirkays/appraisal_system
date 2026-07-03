append_str = """

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
"""

with open('c:\\Users\\sirkays\\Desktop\\workspace\\appriasal_system\\hr_admin\\views.py', 'a', encoding='utf-8') as f:
    f.write(append_str)
