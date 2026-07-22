from django.urls import path
from . import views

app_name = 'appraisals'

urlpatterns = [
    # Staff self-appraisal
    path('self/', views.self_appraisal_form, name='self_appraisal_form'),
    path('self/<int:pk>/', views.self_appraisal_form, name='self_appraisal_form_pk'),

    # My appraisals list
    path('my/', views.my_appraisals, name='my_appraisals'),

    # Universal dynamic step review (for all reviewer roles)
    path('review/<int:pk>/', views.step_review, name='step_review'),

    # Reviewer queue — shows pending assignments
    path('queue/', views.my_review_queue, name='review_queue'),

    # Appraisal final result + acknowledgement
    path('<int:pk>/result/', views.appraisal_result, name='appraisal_result'),
    path('<int:pk>/result/download/', views.download_appraisal_result, name='download_appraisal_result'),
    path('<int:pk>/acknowledge/', views.acknowledge_appraisal, name='acknowledge_appraisal'),

    # Team / department list views (legacy but still useful)
    path('team/', views.team_list, name='team_list'),
    path('department/', views.department_appraisals, name='department_appraisals'),
    path('department/reports/', views.department_reports, name='department_reports'),

    # Legacy compatibility URLs (redirect to step_review)
    path('supervisor-review/<int:pk>/', views.supervisor_review, name='supervisor_review'),
    path('hod-review/<int:pk>/', views.hod_review, name='hod_review'),
]
