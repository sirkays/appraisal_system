from django.urls import path
from . import views

app_name = 'hr_admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Cycle Management
    path('cycles/', views.cycle_list, name='cycle_list'),
    path('cycles/create/', views.cycle_create, name='cycle_create'),
    path('cycles/<int:pk>/clone/', views.cycle_clone, name='cycle_clone'),
    path('cycles/<int:pk>/delete/', views.cycle_delete, name='cycle_delete'),
    path('cycles/<int:pk>/', views.cycle_detail, name='cycle_detail'),
    path('cycles/<int:pk>/edit/', views.cycle_edit, name='cycle_edit'),
    path('cycles/<int:pk>/settings/', views.cycle_settings, name='cycle_settings'),
    path('cycles/<int:cycle_pk>/readd/<int:staff_id>/', views.readd_staff, name='readd_staff'),
    path('appraisals/<int:pk>/remove/', views.remove_appraisal, name='remove_appraisal'),

    # Approval Process Management
    path('cycles/<int:cycle_pk>/approval/', views.approval_process_list, name='approval_process_list'),
    path('cycles/<int:cycle_pk>/approval/create/', views.approval_process_create, name='approval_process_create'),
    path('cycles/<int:cycle_pk>/approval/<int:process_pk>/edit/', views.approval_process_create, name='approval_process_edit'),
    path('cycles/<int:cycle_pk>/approval/<int:process_pk>/delete/', views.approval_process_delete, name='approval_process_delete'),
    path('cycles/<int:cycle_pk>/assign-approvers/', views.assign_approvers, name='assign_approvers'),
    path('cycles/<int:cycle_pk>/assign-approvers/api/', views.api_assign_approver, name='api_assign_approver'),
    path('cycles/<int:cycle_pk>/assign-approvers/api/bulk/', views.api_bulk_assign, name='api_bulk_assign'),
    path('appraisals/<int:appraisal_pk>/override-process/', views.set_override_process, name='set_override_process'),

    # Staff Management
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),

    # Department Management
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),

    # Branch Management
    path('branches/', views.branch_list, name='branch_list'),
    path('branches/create/', views.branch_create, name='branch_create'),
    path('branches/<int:pk>/edit/', views.branch_edit, name='branch_edit'),
    path('branches/<int:pk>/delete/', views.branch_delete, name='branch_delete'),
    path('api/branch/<int:branch_pk>/data/', views.api_branch_data, name='api_branch_data'),

    # Reports
    path('reports/', views.reports_dashboard, name='reports'),
]
