"""
Models for the Performance Appraisals app.

Defines the complete appraisal workflow for the State Internal Revenue Service,
including appraisal cycles, KPI and competency frameworks, scoring, and
multi-level review (self → supervisor → HOD).
"""

from django.db import models
from django.conf import settings


class AppraisalCycle(models.Model):
    """
    Represents a performance appraisal period (e.g., '2025 Annual Review').

    A cycle defines the time window, scoring scale, and status for a batch
    of staff appraisals. KPI and competency frameworks are scoped to a cycle.
    """

    # --- Frequency choices ---
    ANNUAL = 'ANNUAL'
    BI_ANNUAL = 'BI_ANNUAL'
    QUARTERLY = 'QUARTERLY'

    FREQUENCY_CHOICES = [
        (ANNUAL, 'Annual'),
        (BI_ANNUAL, 'Bi-Annual'),
        (QUARTERLY, 'Quarterly'),
    ]

    # --- Status choices ---
    DRAFT = 'DRAFT'
    ACTIVE = 'ACTIVE'
    CLOSED = 'CLOSED'

    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (ACTIVE, 'Active'),
        (CLOSED, 'Closed'),
    ]

    # --- Scoring scale choices ---
    SCORING_SCALE_CHOICES = [
        (5, '1-5 Scale'),
        (10, '1-10 Scale'),
    ]

    name = models.CharField(max_length=200)
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default=ANNUAL,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT,
    )
    scoring_scale = models.PositiveSmallIntegerField(
        choices=SCORING_SCALE_CHOICES,
        default=5,
    )
    target_departments = models.ManyToManyField(
        'departments.Department',
        blank=True,
        help_text="If set, only staff in these departments will be assigned this cycle."
    )
    target_staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='targeted_cycles',
        help_text="If set, these specific staff will be assigned this cycle."
    )
    excluded_staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='excluded_cycles',
        help_text="Staff in this list will never be assigned this cycle."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_cycles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Appraisal Cycle'
        verbose_name_plural = 'Appraisal Cycles'

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        """Return True if the cycle is currently active."""
        return self.status == self.ACTIVE


class KPICategory(models.Model):
    """
    A grouping of related KPI items within an appraisal cycle.

    Each category carries a percentage weight that determines how much
    it contributes to the overall KPI score.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cycle = models.ForeignKey(
        AppraisalCycle,
        on_delete=models.CASCADE,
        related_name='kpi_categories',
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Percentage weight of this category in the overall KPI score.',
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'KPI Category'
        verbose_name_plural = 'KPI Categories'

    def __str__(self):
        return f"{self.name} ({self.cycle.name})"


class KPIItem(models.Model):
    """
    An individual KPI metric within a category.

    Staff will score themselves against each item, and supervisors will
    provide their own scores during the review stage.
    """

    category = models.ForeignKey(
        KPICategory,
        on_delete=models.CASCADE,
        related_name='items',
    )
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'KPI Item'
        verbose_name_plural = 'KPI Items'

    def __str__(self):
        return self.name


class CompetencyCategory(models.Model):
    """
    A grouping of related competency items within an appraisal cycle.

    Competencies assess behavioural and skill-based attributes alongside
    the quantitative KPI framework.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cycle = models.ForeignKey(
        AppraisalCycle,
        on_delete=models.CASCADE,
        related_name='competency_categories',
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Percentage weight of this category in the overall competency score.',
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Competency Category'
        verbose_name_plural = 'Competency Categories'

    def __str__(self):
        return f"{self.name} ({self.cycle.name})"


class CompetencyItem(models.Model):
    """
    An individual competency indicator within a category.
    """

    category = models.ForeignKey(
        CompetencyCategory,
        on_delete=models.CASCADE,
        related_name='items',
    )
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Competency Item'
        verbose_name_plural = 'Competency Items'

    def __str__(self):
        return self.name


class NarrativeField(models.Model):
    """
    A configurable narrative field for an appraisal cycle
    (e.g., 'Key Achievements', 'Performance Challenges').
    """
    cycle = models.ForeignKey(
        AppraisalCycle,
        on_delete=models.CASCADE,
        related_name='narrative_fields',
    )
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    is_supervisor_field = models.BooleanField(
        default=False,
        help_text="If True, this field is filled by the supervisor instead of the staff member."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Narrative Field'
        verbose_name_plural = 'Narrative Fields'

    def __str__(self):
        return self.name


class Appraisal(models.Model):
    """
    A single staff member's appraisal within a given cycle.

    Tracks the full workflow from self-assessment through supervisor
    and HOD review, including all aggregate scores.
    """

    # --- Status choices ---
    NOT_STARTED = 'NOT_STARTED'
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    UNDER_REVIEW = 'UNDER_REVIEW'
    RETURNED_TO_STAFF = 'RETURNED_TO_STAFF'
    REVIEWED = 'REVIEWED'
    RETURNED_TO_SUPERVISOR = 'RETURNED_TO_SUPERVISOR'
    APPROVED = 'APPROVED'
    ARCHIVED = 'ARCHIVED'

    STATUS_CHOICES = [
        (NOT_STARTED, 'Not Started'),
        (DRAFT, 'Draft'),
        (SUBMITTED, 'Submitted'),
        (UNDER_REVIEW, 'Under Review'),
        (RETURNED_TO_STAFF, 'Returned to Staff'),
        (REVIEWED, 'Reviewed'),
        (RETURNED_TO_SUPERVISOR, 'Returned to Supervisor'),
        (APPROVED, 'Approved'),
        (ARCHIVED, 'Archived'),
    ]

    cycle = models.ForeignKey(
        AppraisalCycle,
        on_delete=models.CASCADE,
        related_name='appraisals',
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appraisals',
    )
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default=NOT_STARTED,
    )
    self_submitted_at = models.DateTimeField(null=True, blank=True)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_appraisals',
    )
    supervisor_reviewed_at = models.DateTimeField(null=True, blank=True)
    hod_reviewed_at = models.DateTimeField(null=True, blank=True)
    overall_self_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    overall_supervisor_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    final_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    supervisor_return_notes = models.TextField(
        blank=True,
        help_text="Reason provided by the supervisor when returning the appraisal to the staff."
    )
    hod_return_notes = models.TextField(
        blank=True,
        help_text="Reason provided by the HOD when returning the appraisal to the supervisor."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('cycle', 'staff')]
        verbose_name = 'Appraisal'
        verbose_name_plural = 'Appraisals'

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.cycle.name}"

    @property
    def has_supervisor_draft(self):
        """Returns True if the supervisor has started reviewing but hasn't submitted yet."""
        if self.status != self.SUBMITTED:
            return False
            
        # Check if there's any supervisor score
        if self.kpi_scores.filter(supervisor_score__isnull=False).exists():
            return True
        if self.competency_scores.filter(supervisor_score__isnull=False).exists():
            return True
            
        # Check if supervisor review has any text content
        if hasattr(self, 'supervisor_review'):
            if self.supervisor_review.overall_comments or self.supervisor_review.recommendation:
                return True
                
        return False


class KPIScore(models.Model):
    """
    Records the self and supervisor scores for a single KPI item
    within an appraisal, along with target/achievement narratives.
    """

    appraisal = models.ForeignKey(
        Appraisal,
        on_delete=models.CASCADE,
        related_name='kpi_scores',
    )
    kpi_item = models.ForeignKey(
        KPIItem,
        on_delete=models.CASCADE,
    )
    target = models.TextField(
        blank=True,
        help_text='What was the target for this KPI.',
    )
    achievement = models.TextField(
        blank=True,
        help_text='What was achieved against the target.',
    )
    self_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    supervisor_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    staff_comment = models.TextField(blank=True)
    supervisor_comment = models.TextField(blank=True)
    evidence_file = models.FileField(
        upload_to='evidence/kpis/',
        null=True,
        blank=True,
        help_text='Optional file attachment to provide evidence for this KPI.'
    )

    class Meta:
        unique_together = [('appraisal', 'kpi_item')]
        verbose_name = 'KPI Score'
        verbose_name_plural = 'KPI Scores'

    def __str__(self):
        return f"{self.appraisal.staff.get_full_name()} - {self.kpi_item.name}"


class CompetencyScore(models.Model):
    """
    Records the self and supervisor scores for a single competency item
    within an appraisal.
    """

    appraisal = models.ForeignKey(
        Appraisal,
        on_delete=models.CASCADE,
        related_name='competency_scores',
    )
    competency_item = models.ForeignKey(
        CompetencyItem,
        on_delete=models.CASCADE,
    )
    self_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    supervisor_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    staff_comment = models.TextField(blank=True)
    supervisor_comment = models.TextField(blank=True)
    evidence_file = models.FileField(
        upload_to='evidence/competencies/',
        null=True,
        blank=True,
        help_text='Optional file attachment to provide evidence for this Competency.'
    )

    class Meta:
        unique_together = [('appraisal', 'competency_item')]
        verbose_name = 'Competency Score'
        verbose_name_plural = 'Competency Scores'

    def __str__(self):
        return f"{self.appraisal.staff.get_full_name()} - {self.competency_item.name}"


class SupervisorReview(models.Model):
    """
    The supervisor's qualitative review of a staff appraisal, including
    an overall recommendation and narrative feedback.
    """

    # --- Recommendation choices ---
    EXCELLENT = 'EXCELLENT'
    VERY_GOOD = 'VERY_GOOD'
    GOOD = 'GOOD'
    FAIR = 'FAIR'
    POOR = 'POOR'

    RECOMMENDATION_CHOICES = [
        (EXCELLENT, 'Excellent'),
        (VERY_GOOD, 'Very Good'),
        (GOOD, 'Good'),
        (FAIR, 'Fair'),
        (POOR, 'Poor'),
    ]

    appraisal = models.OneToOneField(
        Appraisal,
        on_delete=models.CASCADE,
        related_name='supervisor_review',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='supervisor_reviews',
    )
    overall_comments = models.TextField(blank=True)
    recommendation = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_CHOICES,
        blank=True,
    )
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Supervisor Review'
        verbose_name_plural = 'Supervisor Reviews'

    def __str__(self):
        return f"Supervisor Review: {self.appraisal}"


class HODReview(models.Model):
    """
    Head of Department review — the final approval or return step
    in the appraisal workflow.
    """

    # --- Action choices ---
    APPROVED = 'APPROVED'
    RETURNED = 'RETURNED'

    ACTION_CHOICES = [
        (APPROVED, 'Approved'),
        (RETURNED, 'Returned'),
    ]

    appraisal = models.OneToOneField(
        Appraisal,
        on_delete=models.CASCADE,
        related_name='hod_review',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='hod_reviews',
    )
    comments = models.TextField(blank=True)
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
    )
    reviewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'HOD Review'
        verbose_name_plural = 'HOD Reviews'

    def __str__(self):
        return f"HOD Review for {self.appraisal.staff.full_name}"


class NarrativeResponse(models.Model):
    """
    Staff or supervisor response to a NarrativeField.
    """
    appraisal = models.ForeignKey(
        Appraisal,
        on_delete=models.CASCADE,
        related_name='narrative_responses'
    )
    field = models.ForeignKey(
        NarrativeField,
        on_delete=models.CASCADE
    )
    response_text = models.TextField(blank=True)
    evidence_file = models.FileField(
        upload_to='evidence/narratives/',
        null=True,
        blank=True
    )

    class Meta:
        unique_together = [('appraisal', 'field')]
        verbose_name = 'Narrative Response'
        verbose_name_plural = 'Narrative Responses'

    def __str__(self):
        return f"Response to {self.field.name} for {self.appraisal.staff.full_name}"
