"""
Admin configuration for the CBT module.
"""
from django.contrib import admin
from .models import (
    CBTExam, CBTQuestion, CBTOption,
    CBTAssignment, CBTAttempt, CBTAnswer,
)


class CBTOptionInline(admin.TabularInline):
    model = CBTOption
    extra = 4
    fields = ("text", "is_correct", "order")


class CBTQuestionInline(admin.StackedInline):
    model = CBTQuestion
    extra = 1
    fields = ("text", "marks", "order")
    show_change_link = True


@admin.register(CBTExam)
class CBTExamAdmin(admin.ModelAdmin):
    list_display = (
        "title", "status", "duration_minutes", "pass_mark",
        "question_count", "total_marks", "randomise_questions",
        "allow_multiple_attempts", "created_by", "created_at",
    )
    list_filter = ("status", "randomise_questions", "allow_multiple_attempts")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CBTQuestionInline]

    def question_count(self, obj):
        return obj.question_count
    question_count.short_description = "Questions"

    def total_marks(self, obj):
        return obj.total_marks
    total_marks.short_description = "Total Marks"


@admin.register(CBTQuestion)
class CBTQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "exam", "marks", "order")
    list_filter = ("exam",)
    search_fields = ("text",)
    inlines = [CBTOptionInline]


@admin.register(CBTOption)
class CBTOptionAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "is_correct", "order")
    list_filter = ("is_correct",)
    search_fields = ("text",)


@admin.register(CBTAssignment)
class CBTAssignmentAdmin(admin.ModelAdmin):
    list_display = ("exam", "assign_to_all", "deadline", "created_at")
    list_filter = ("assign_to_all",)
    filter_horizontal = ("target_staff", "target_departments")


class CBTAnswerInline(admin.TabularInline):
    model = CBTAnswer
    extra = 0
    readonly_fields = ("question", "selected_option", "is_correct")
    can_delete = False

    def is_correct(self, obj):
        return obj.is_correct
    is_correct.boolean = True


@admin.register(CBTAttempt)
class CBTAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "staff", "exam", "status", "raw_score", "total_marks",
        "percentage", "passed", "started_at", "submitted_at",
    )
    list_filter = ("status", "passed", "exam")
    search_fields = ("staff__first_name", "staff__last_name", "exam__title")
    readonly_fields = (
        "staff", "exam", "status", "raw_score", "total_marks",
        "percentage", "passed", "started_at", "submitted_at",
        "question_order", "created_at",
    )
    inlines = [CBTAnswerInline]
