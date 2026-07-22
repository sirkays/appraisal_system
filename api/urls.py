from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Auth
    path('auth/login/', views.AuthLoginView.as_view(), name='auth_login'),
    path('auth/logout/', views.AuthLogoutView.as_view(), name='auth_logout'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='auth_change_password'),
    path('me/', views.UserProfileView.as_view(), name='user_profile'),
    path('me/avatar/', views.UserProfileAvatarView.as_view(), name='user_profile_avatar'),

    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # Cycles — only cycles the authenticated user is eligible for
    path('cycles/', views.CyclesListView.as_view(), name='cycles_list'),
    path('cycles/switch/', views.SwitchCycleView.as_view(), name='cycles_switch'),

    # Staff Appraisals
    path('appraisals/start/', views.StartAppraisalView.as_view(), name='start_appraisal'),
    path('appraisals/my/', views.MyAppraisalsListView.as_view(), name='my_appraisals'),
    path('appraisals/<int:pk>/', views.AppraisalDetailView.as_view(), name='appraisal_detail'),
    path('appraisals/<int:pk>/self-submit/', views.SelfAppraisalSubmitView.as_view(), name='self_appraisal_submit'),
    path('appraisals/<int:pk>/evidence/', views.FormFieldEvidenceUploadView.as_view(), name='appraisal_evidence_upload'),
    path('appraisals/<int:pk>/acknowledge/', views.AcknowledgeAppraisalView.as_view(), name='acknowledge_appraisal'),
    path('appraisals/<int:pk>/return-history/', views.AppraisalReturnHistoryView.as_view(), name='appraisal_return_history'),

    # Reviewer Queue & Step Review
    path('review/queue/', views.ReviewQueueListView.as_view(), name='review_queue'),
    path('review/history/', views.ReviewHistoryListView.as_view(), name='review_history'),
    path('review/<int:pk>/step/', views.StepReviewSubmitView.as_view(), name='step_review_submit'),

    # Notifications
    path('notifications/', views.NotificationsListView.as_view(), name='notifications_list'),
    path('notifications/<int:pk>/read/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),

    # HR Administration APIs
    path('hr/dashboard/', views.HRDashboardView.as_view(), name='hr_dashboard'),
    path('hr/staff/', views.HRStaffListView.as_view(), name='hr_staff_list'),
    path('hr/departments/', views.HRDepartmentsListView.as_view(), name='hr_departments_list'),
    path('hr/branches/', views.HRBranchesListView.as_view(), name='hr_branches_list'),
    path('hr/reports/', views.HRReportsView.as_view(), name='hr_reports'),
]

