"""
Admin configuration for the Performance Appraisals app.

Provides rich admin interfaces with inline editing for the full
appraisal workflow: cycles, KPI/competency frameworks, scoring, and reviews.
"""

from django.contrib import admin

from accounts.admin import AppraisalAdminPermissionMixin

class BaseAppraisalModelAdmin(AppraisalAdminPermissionMixin, admin.ModelAdmin):
    pass

class BaseTabularInline(AppraisalAdminPermissionMixin, admin.TabularInline):
    pass

class BaseStackedInline(AppraisalAdminPermissionMixin, admin.StackedInline):
    pass

from .models import (
    AppraisalCycle,
    KPICategory,
    KPIItem,
    CompetencyCategory,
    CompetencyItem,
    Appraisal,
    KPIScore,
    CompetencyScore,
    NarrativeField,
    NarrativeResponse,
    SupervisorReview,
    HODReview,
)


# ---------------------------------------------------------------------------
# Appraisal Cycle
# ---------------------------------------------------------------------------

class NarrativeFieldInline(BaseTabularInline):
    model = NarrativeField
    extra = 1


@admin.register(AppraisalCycle)
class AppraisalCycleAdmin(BaseAppraisalModelAdmin):
    list_display = ('name', 'frequency', 'start_date', 'end_date', 'status', 'scoring_scale')
    list_filter = ('status', 'frequency')
    search_fields = ('name',)
    inlines = [NarrativeFieldInline]


# ---------------------------------------------------------------------------
# KPI Framework — Category with inline Items
# ---------------------------------------------------------------------------

class KPIItemInline(BaseTabularInline):
    model = KPIItem
    extra = 1


@admin.register(KPICategory)
class KPICategoryAdmin(BaseAppraisalModelAdmin):
    list_display = ('name', 'cycle', 'weight', 'order')
    list_filter = ('cycle',)
    search_fields = ('name',)
    inlines = [KPIItemInline]


@admin.register(KPIItem)
class KPIItemAdmin(BaseAppraisalModelAdmin):
    list_display = ('name', 'category', 'weight', 'order')
    list_filter = ('category__cycle',)
    search_fields = ('name',)


# ---------------------------------------------------------------------------
# Competency Framework — Category with inline Items
# ---------------------------------------------------------------------------

class CompetencyItemInline(BaseTabularInline):
    model = CompetencyItem
    extra = 1


@admin.register(CompetencyCategory)
class CompetencyCategoryAdmin(BaseAppraisalModelAdmin):
    list_display = ('name', 'cycle', 'weight', 'order')
    list_filter = ('cycle',)
    search_fields = ('name',)
    inlines = [CompetencyItemInline]


@admin.register(CompetencyItem)
class CompetencyItemAdmin(BaseAppraisalModelAdmin):
    list_display = ('name', 'category', 'weight', 'order')
    list_filter = ('category__cycle',)
    search_fields = ('name',)


# ---------------------------------------------------------------------------
# Appraisal — with all score & review inlines
# ---------------------------------------------------------------------------

class KPIScoreInline(BaseTabularInline):
    model = KPIScore
    extra = 0


class CompetencyScoreInline(BaseTabularInline):
    model = CompetencyScore
    extra = 0


class NarrativeResponseInline(BaseStackedInline):
    model = NarrativeResponse
    extra = 0
    max_num = 1


class SupervisorReviewInline(BaseStackedInline):
    model = SupervisorReview
    extra = 0
    max_num = 1


class HODReviewInline(BaseStackedInline):
    model = HODReview
    extra = 0
    max_num = 1


@admin.register(Appraisal)
class AppraisalAdmin(BaseAppraisalModelAdmin):
    list_display = (
        'staff',
        'cycle',
        'status',
        'overall_self_score',
        'overall_supervisor_score',
        'final_score',
    )
    list_filter = ('status', 'cycle')
    search_fields = (
        'staff__first_name',
        'staff__last_name',
        'staff__staff_id',
    )
    inlines = [
        KPIScoreInline,
        CompetencyScoreInline,
        NarrativeResponseInline,
        SupervisorReviewInline,
        HODReviewInline,
    ]


# ---------------------------------------------------------------------------
# Standalone registrations for score & review models
# ---------------------------------------------------------------------------

@admin.register(KPIScore)
class KPIScoreAdmin(BaseAppraisalModelAdmin):
    list_display = ('appraisal', 'kpi_item', 'self_score', 'supervisor_score')
    list_filter = ('appraisal__cycle',)


@admin.register(CompetencyScore)
class CompetencyScoreAdmin(BaseAppraisalModelAdmin):
    list_display = ('appraisal', 'competency_item', 'self_score', 'supervisor_score')
    list_filter = ('appraisal__cycle',)


@admin.register(SupervisorReview)
class SupervisorReviewAdmin(BaseAppraisalModelAdmin):
    list_display = ('appraisal', 'reviewer', 'recommendation', 'reviewed_at')
    list_filter = ('recommendation',)


@admin.register(HODReview)
class HODReviewAdmin(BaseAppraisalModelAdmin):
    list_display = ('appraisal', 'reviewer', 'action', 'reviewed_at')
    list_filter = ('action',)


@admin.register(NarrativeField)
class NarrativeFieldAdmin(BaseAppraisalModelAdmin):
    list_display = ('name', 'cycle', 'is_supervisor_field', 'order')
    list_filter = ('cycle', 'is_supervisor_field')
    search_fields = ('name',)


@admin.register(NarrativeResponse)
class NarrativeResponseAdmin(BaseAppraisalModelAdmin):
    list_display = ('appraisal', 'field', 'response_text_truncated')
    list_filter = ('field__cycle',)
    search_fields = ('response_text', 'appraisal__staff__first_name', 'appraisal__staff__last_name')

    def response_text_truncated(self, obj):
        return obj.response_text[:50] + '...' if len(obj.response_text) > 50 else obj.response_text
    response_text_truncated.short_description = 'Response Text'
