from django.urls import path
from . import views

app_name = 'hr_admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Cycle Management
    path('cycles/', views.cycle_list, name='cycle_list'),
    path('cycles/create/', views.cycle_create, name='cycle_create'),
    path('cycles/<int:pk>/', views.cycle_detail, name='cycle_detail'),
    path('cycles/<int:pk>/edit/', views.cycle_edit, name='cycle_edit'),
    path('cycles/<int:pk>/settings/', views.cycle_settings, name='cycle_settings'),
    path('cycles/<int:cycle_pk>/readd/<int:staff_id>/', views.readd_staff, name='readd_staff'),
    path('appraisals/<int:pk>/remove/', views.remove_appraisal, name='remove_appraisal'),

    # Staff Management
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),

    # Department Management
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),

    # Reports
    path('reports/', views.reports_dashboard, name='reports'),
]
