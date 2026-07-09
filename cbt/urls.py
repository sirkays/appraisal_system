"""
URL configuration for the CBT module.

Staff routes:
    cbt/                         → exam_list
    cbt/exam/<pk>/               → exam_detail
    cbt/exam/<pk>/start/         → start_exam  (POST, creates attempt)
    cbt/attempt/<pk>/take/       → take_exam   (timed exam UI)
    cbt/attempt/<pk>/submit/     → submit_exam (POST)
    cbt/attempt/<pk>/result/     → exam_result
    cbt/my-results/              → my_results

HR Admin routes:
    cbt/hr/                      → hr_exam_list
    cbt/hr/exam/create/          → hr_exam_create
    cbt/hr/exam/<pk>/edit/       → hr_exam_edit
    cbt/hr/exam/<pk>/delete/     → hr_exam_delete
    cbt/hr/exam/<pk>/questions/  → hr_question_manager
    cbt/hr/exam/<pk>/questions/<qpk>/delete/ → hr_question_delete
    cbt/hr/exam/<pk>/assign/     → hr_exam_assign
    cbt/hr/exam/<pk>/results/    → hr_exam_results
"""

from django.urls import path
from . import views

app_name = "cbt"

urlpatterns = [
    # ── Staff ──────────────────────────────────────────────────────────────
    path("", views.exam_list, name="exam_list"),
    path("exam/<int:pk>/", views.exam_detail, name="exam_detail"),
    path("exam/<int:pk>/start/", views.start_exam, name="start_exam"),
    path("attempt/<int:pk>/take/", views.take_exam, name="take_exam"),
    path("attempt/<int:pk>/submit/", views.submit_exam, name="submit_exam"),
    path("attempt/<int:pk>/result/", views.exam_result, name="exam_result"),
    path("my-results/", views.my_results, name="my_results"),

    # ── HR Admin ────────────────────────────────────────────────────────────
    path("hr/", views.hr_exam_list, name="hr_exam_list"),
    path("hr/exam/create/", views.hr_exam_create, name="hr_exam_create"),
    path("hr/exam/<int:pk>/edit/", views.hr_exam_edit, name="hr_exam_edit"),
    path("hr/exam/<int:pk>/delete/", views.hr_exam_delete, name="hr_exam_delete"),
    path("hr/exam/<int:pk>/questions/", views.hr_question_manager, name="hr_question_manager"),
    path("hr/exam/<int:pk>/questions/<int:qpk>/delete/", views.hr_question_delete, name="hr_question_delete"),
    path("hr/exam/<int:pk>/options/<int:opk>/delete/", views.hr_option_delete, name="hr_option_delete"),
    path("hr/exam/<int:pk>/assign/", views.hr_exam_assign, name="hr_exam_assign"),
    path("hr/exam/<int:pk>/results/", views.hr_exam_results, name="hr_exam_results"),
]
