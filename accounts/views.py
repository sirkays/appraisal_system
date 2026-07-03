from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth import logout as django_logout
from django.contrib import messages
from django.http import HttpResponseForbidden
from accounts.models import CustomUser
from appraisals.models import AppraisalCycle, Appraisal, KPIItem, CompetencyItem

class LoginView(DjangoLoginView):
    """Custom LoginView referencing the styled login template."""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy_placeholder_or_redirect(self.request.user)

def reverse_lazy_placeholder_or_redirect(user):
    """Helper to determine the routing target based on user role."""
    if user.role == CustomUser.HR_ADMIN:
        from django.urls import reverse
        return reverse('hr_admin:dashboard')
    elif user.role == CustomUser.HOD:
        return '/hod/dashboard/'
    elif user.role == CustomUser.SUPERVISOR:
        return '/supervisor/dashboard/'
    else:
        return '/staff/dashboard/'

@login_required
def dashboard_redirect(request):
    """Redirects users to their appropriate dashboard based on their role."""
    return redirect(reverse_lazy_placeholder_or_redirect(request.user))

def logout_view(request):
    """Logs out the user and redirects to the login page with a success message."""
    django_logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('accounts:login')

# --- Role-Based Dashboard Views ---

@login_required
def staff_dashboard(request):
    # Get active cycle and associated appraisal
    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()
    appraisal = None
    progress = 0
    status_display = "Not Started"
    
    if active_cycle:
        appraisal = Appraisal.objects.filter(cycle=active_cycle, staff=request.user).first()
        if appraisal:
            status_display = appraisal.get_status_display()
            if appraisal.status in [Appraisal.SUBMITTED, Appraisal.REVIEWED, Appraisal.APPROVED, Appraisal.ARCHIVED]:
                progress = 100
            else:
                # Calculate draft completion progress
                kpis_count = KPIItem.objects.filter(category__cycle=active_cycle).count()
                comps_count = CompetencyItem.objects.filter(category__cycle=active_cycle).count()
                total_items = kpis_count + comps_count
                
                scored_kpis = appraisal.kpi_scores.filter(self_score__isnull=False).count()
                scored_comps = appraisal.competency_scores.filter(self_score__isnull=False).count()
                scored_items = scored_kpis + scored_comps
                
                progress = int((scored_items / total_items) * 100) if total_items > 0 else 0
                
    context = {
        'active_cycle': active_cycle,
        'appraisal': appraisal,
        'status_display': status_display,
        'progress': progress,
    }
    return render(request, 'accounts/dashboards/staff.html', context)

@login_required
def supervisor_dashboard(request):
    if request.user.role != CustomUser.SUPERVISOR:
        return redirect('accounts:dashboard_redirect')
        
    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()
    
    context = {
        'active_cycle': active_cycle,
        'total_team': 0,
        'pending_self': 0,
        'awaiting_review': 0,
        'reviewed': 0,
        'recent_submissions': []
    }
    
    if active_cycle:
        team_appraisals = Appraisal.objects.filter(supervisor=request.user, cycle=active_cycle).select_related('staff')
        
        pending_self = team_appraisals.filter(status__in=[Appraisal.NOT_STARTED, Appraisal.DRAFT, Appraisal.RETURNED_TO_STAFF]).count()
        awaiting_review = team_appraisals.filter(status__in=[Appraisal.SUBMITTED, Appraisal.RETURNED_TO_SUPERVISOR]).count()
        reviewed = team_appraisals.filter(status__in=[Appraisal.UNDER_REVIEW, Appraisal.APPROVED, Appraisal.ARCHIVED, Appraisal.REVIEWED]).count()
        
        context.update({
            'total_team': team_appraisals.count(),
            'pending_self': pending_self,
            'awaiting_review': awaiting_review,
            'reviewed': reviewed,
            'recent_submissions': team_appraisals.filter(status__in=[Appraisal.SUBMITTED, Appraisal.RETURNED_TO_SUPERVISOR]).order_by('-self_submitted_at')[:5]
        })
        
    return render(request, 'accounts/dashboards/supervisor.html', context)

@login_required
def hod_dashboard(request):
    if request.user.role != CustomUser.HOD:
        return redirect('accounts:dashboard_redirect')
        
    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()
    
    context = {
        'active_cycle': active_cycle,
        'total_dept_staff': 0,
        'awaiting_approval': 0,
        'approved': 0,
        'recent_submissions': []
    }
    
    if active_cycle and request.user.department:
        # Get all staff in the HOD's department, excluding the HOD themselves (optional, but HOD is usually evaluated differently)
        # We include all staff in the department
        dept_staff = CustomUser.objects.filter(department=request.user.department)
        dept_appraisals = Appraisal.objects.filter(staff__in=dept_staff, cycle=active_cycle).select_related('staff')
        
        awaiting_approval = dept_appraisals.filter(status=Appraisal.UNDER_REVIEW).count()
        approved = dept_appraisals.filter(status__in=[Appraisal.APPROVED, Appraisal.ARCHIVED]).count()
        
        context.update({
            'total_dept_staff': dept_staff.count(),
            'awaiting_approval': awaiting_approval,
            'approved': approved,
            'recent_submissions': dept_appraisals.filter(status=Appraisal.UNDER_REVIEW).order_by('-supervisor_reviewed_at')[:5]
        })
        
    return render(request, 'accounts/dashboards/hod.html', context)

@login_required
def admin_dashboard(request):
    if request.user.role == CustomUser.HR_ADMIN:
        return redirect('hr_admin:dashboard')
    elif request.user.role != CustomUser.HR_ADMIN:
        return redirect('accounts:dashboard_redirect')
    return render(request, 'accounts/dashboards/admin.html')
