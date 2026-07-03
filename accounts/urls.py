from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path('', views.dashboard_redirect, name='index'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/redirect/', views.dashboard_redirect, name='dashboard_redirect'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('supervisor/dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('hod/dashboard/', views.hod_dashboard, name='hod_dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
