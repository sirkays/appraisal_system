from django.urls import path
from . import views

app_name = 'appraisals'

urlpatterns = [
    path('self/', views.self_appraisal_form, name='self_appraisal_form'),
    path('self/<int:pk>/', views.self_appraisal_form, name='self_appraisal_form_pk'),
    path('my/', views.my_appraisals, name='my_appraisals'),
    path('team/', views.team_list, name='team_list'),
    path('review/<int:pk>/', views.supervisor_review, name='supervisor_review'),
    path('department/', views.department_appraisals, name='department_appraisals'),
    path('hod-review/<int:pk>/', views.hod_review, name='hod_review'),
]
