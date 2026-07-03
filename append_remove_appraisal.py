append_str = """
@login_required
def remove_appraisal(request, pk):
    if request.user.role != 'HR_ADMIN':
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    from appraisals.models import Appraisal
    appraisal = get_object_or_404(Appraisal, pk=pk)
    
    if request.method == 'POST':
        if appraisal.status == Appraisal.NOT_STARTED:
            # Add to excluded_staff so they aren't recreated on sync
            appraisal.cycle.excluded_staff.add(appraisal.staff)
            appraisal.delete()
            messages.success(request, f"Appraisal for {appraisal.staff.full_name} removed successfully.")
        else:
            messages.error(request, f"Cannot remove {appraisal.staff.full_name} because they have already started their appraisal.")
            
    return redirect('hr_admin:cycle_settings', pk=appraisal.cycle.pk)
"""

with open('c:\\Users\\sirkays\\Desktop\\workspace\\appriasal_system\\hr_admin\\views.py', 'a', encoding='utf-8') as f:
    f.write(append_str)
