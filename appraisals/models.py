"""
Models for the Performance Appraisals app.

Defines the complete appraisal workflow for the Staff Appraisal Organization,
including appraisal cycles, KPI and competency frameworks, scoring, and
fully dynamic multi-step approval processes (general per-cycle and per-staff overrides).
"""

from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone


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
    ARCHIVED = 'ARCHIVED'

    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (ACTIVE, 'Active'),
        (CLOSED, 'Closed'),
        (ARCHIVED, 'Archived'),
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
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cycles',
        help_text="Branch this cycle is scoped to. All targeting is filtered by this branch.",
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
    archived_at = models.DateTimeField(null=True, blank=True)

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

    @property
    def has_submitted_appraisals(self):
        """Return True once any appraisal in this cycle has been submitted or reviewed."""
        return (
            self.appraisals.exclude(status__in=['NOT_STARTED', 'DRAFT']).exists()
            or self.appraisals.filter(self_submitted_at__isnull=False).exists()
        )

    @property
    def can_be_deleted(self):
        """Cycles are deletable before submission, or 30 days after archival."""
        if not self.has_submitted_appraisals:
            return True
        return self.status == self.ARCHIVED and self.archived_at and timezone.now() >= self.archived_at + timedelta(days=30)

    @property
    def archive_delete_available_at(self):
        """Return when an archived submitted cycle becomes deletable."""
        if self.status == self.ARCHIVED and self.archived_at and self.has_submitted_appraisals:
            return self.archived_at + timedelta(days=30)
        return None

    @property
    def general_approval_process(self):
        """Return the cycle's designated general (default) approval process."""
        return self.approval_processes.filter(is_general=True).first()


# ============================================================
# APPROVAL WORKFLOW MODELS
# ============================================================

class ApprovalProcess(models.Model):
    """
    Defines a named, ordered chain of approval steps.

    An ApprovalProcess can be:
    - **General** (is_general=True): the default process for all staff in a cycle.
    - **Override**: assigned to a specific staff member's appraisal to replace
      the general process (e.g., for HODs or Directors whose chain differs).

    A single cycle can have many ApprovalProcess records but only ONE general one.
    """

    cycle = models.ForeignKey(
        AppraisalCycle,
        on_delete=models.CASCADE,
        related_name='approval_processes',
    )
    name = models.CharField(
        max_length=200,
        help_text="Descriptive name, e.g. 'Standard 4-Step Review' or 'HOD Override Process'."
    )
    is_general = models.BooleanField(
        default=False,
        help_text="If True, this is the default process applied to all staff in this cycle."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_approval_processes',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_general', 'name']
        verbose_name = 'Approval Process'
        verbose_name_plural = 'Approval Processes'

    def __str__(self):
        flag = " [General]" if self.is_general else ""
        return f"{self.name}{flag} — {self.cycle.name}"

    @property
    def step_count(self):
        return self.steps.count()


class ApprovalStep(models.Model):
    """
    A single step in an ApprovalProcess.

    Each step specifies which role is required to action it and a human-readable
    label. Steps are ordered by step_number within a process.
    """

    SUPERVISOR = 'SUPERVISOR'
    HOD = 'HOD'
    DIRECTORATE = 'DIRECTORATE'
    HR_ADMIN = 'HR_ADMIN'

    ROLE_CHOICES = [
        (SUPERVISOR, 'Supervisor'),
        (HOD, 'Head of Department'),
        (DIRECTORATE, 'Director/Executive'),
        (HR_ADMIN, 'HR Administrator'),
    ]

    process = models.ForeignKey(
        ApprovalProcess,
        on_delete=models.CASCADE,
        related_name='steps',
    )
    step_number = models.PositiveIntegerField(
        help_text="Ordering within the process. Step 1 is actioned first."
    )
    label = models.CharField(
        max_length=200,
        help_text="Display label, e.g. 'Supervisor Review', 'HOD Moderation'."
    )
    role_required = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Which role is allowed to action this step."
    )
    action_label_approve = models.CharField(
        max_length=100,
        default="Approve & Forward",
        help_text="Button label for the approve action."
    )
    action_label_return = models.CharField(
        max_length=100,
        default="Return for Revision",
        help_text="Button label for the return action."
    )
    can_score = models.BooleanField(
        default=True,
        help_text="If True, the approver at this step can enter/edit scores."
    )

    class Meta:
        ordering = ['step_number']
        unique_together = [('process', 'step_number')]
        verbose_name = 'Approval Step'
        verbose_name_plural = 'Approval Steps'

    def __str__(self):
        return f"Step {self.step_number}: {self.label} ({self.process.name})"


class AppraisalApprovalAssignment(models.Model):
    """
    Links a specific approver user to an ApprovalStep for one specific Appraisal.

    When a cycle is activated (or the approval process is assigned), one
    AppraisalApprovalAssignment record is created per step per appraisal.
    HR Admin can then set the specific `approver` user for each assignment.
    """

    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    RETURNED = 'RETURNED'
    SKIPPED = 'SKIPPED'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (RETURNED, 'Returned'),
        (SKIPPED, 'Skipped'),
    ]

    appraisal = models.ForeignKey(
        'Appraisal',
        on_delete=models.CASCADE,
        related_name='approval_assignments',
    )
    step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_assignments',
        help_text="The specific user assigned to action this step."
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    comments = models.TextField(blank=True)
    actioned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['step__step_number']
        unique_together = [('appraisal', 'step')]
        verbose_name = 'Approval Assignment'
        verbose_name_plural = 'Approval Assignments'

    def __str__(self):
        approver_name = self.approver.get_full_name() if self.approver else "Unassigned"
        return f"{self.appraisal} — Step {self.step.step_number}: {approver_name} [{self.status}]"


# ============================================================
# KPI & COMPETENCY FRAMEWORK
# ============================================================

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

    Staff will score themselves against each item, and approvers will
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
        help_text="If True, this field is filled by the first-step approver instead of the staff member."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Narrative Field'
        verbose_name_plural = 'Narrative Fields'

    def __str__(self):
        return self.name


# ============================================================
# NEW: UNIFIED FORM BUILDER MODELS
# ============================================================

class FormSection(models.Model):
    """
    A named group of FormFields within an appraisal cycle.

    Sections appear in order on the appraisal form.
    Each section carries a weight (% of total score) used when
    computing overall scores. Set weight=0 for pure narrative sections.
    """

    cycle = models.ForeignKey(
        AppraisalCycle,
        on_delete=models.CASCADE,
        related_name='form_sections',
    )
    name = models.CharField(max_length=200, help_text="e.g. 'Section A: KPIs & Core Duties'")
    description = models.TextField(blank=True, help_text="Optional instructions shown above the section.")
    section_weight = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Percentage weight of this section in the overall score (0-100). Set to 0 for non-scored sections."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Form Section'
        verbose_name_plural = 'Form Sections'

    def __str__(self):
        return f"{self.name} ({self.cycle.name})"


class FormField(models.Model):
    """
    A single configurable field within a FormSection.

    Supports 5 field types and can be assigned to any role
    (appraisee or any reviewer in the approval process).
    Score fields carry configurable min/max bounds.
    Select fields store their options as JSON.
    Mode-B fields (reviewer_can_score / reviewer_can_comment) allow
    a reviewer to annotate an appraisee's own field response.
    """

    # ── Field type constants ──────────────────────────────────
    NARRATIVE     = 'NARRATIVE'      # Open text area
    SCORE         = 'SCORE'          # Numeric input with min/max
    SCORE_COMMENT = 'SCORE_COMMENT'  # Numeric input + text comment
    SINGLE_SELECT = 'SINGLE_SELECT'  # Radio buttons (one choice)
    MULTI_SELECT  = 'MULTI_SELECT'   # Checkboxes (multiple choices)

    FIELD_TYPE_CHOICES = [
        (NARRATIVE,     'Narrative (Text)'),
        (SCORE,         'Score (Numeric)'),
        (SCORE_COMMENT, 'Score + Comment'),
        (SINGLE_SELECT, 'Single Select'),
        (MULTI_SELECT,  'Multiple Select'),
    ]

    # ── Who fills this field ──────────────────────────────────
    APPRAISEE   = 'APPRAISEE'
    SUPERVISOR  = 'SUPERVISOR'
    HOD         = 'HOD'
    DIRECTORATE = 'DIRECTORATE'
    HR_ADMIN    = 'HR_ADMIN'

    FILLED_BY_CHOICES = [
        (APPRAISEE,   'Appraisee (Staff)'),
        (SUPERVISOR,  'Supervisor'),
        (HOD,         'Head of Department'),
        (DIRECTORATE, 'Director/Executive'),
        (HR_ADMIN,    'HR Administrator'),
    ]

    section = models.ForeignKey(
        FormSection,
        on_delete=models.CASCADE,
        related_name='fields',
    )
    label = models.CharField(max_length=300, help_text="Display name, e.g. 'Revenue Target Achieved'")
    description = models.TextField(blank=True, help_text="Help text shown beneath the field.")
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default=NARRATIVE,
    )
    filled_by = models.CharField(
        max_length=20,
        choices=FILLED_BY_CHOICES,
        default=APPRAISEE,
        help_text="Which role is responsible for filling this field.",
    )

    # Score bounds (used for SCORE and SCORE_COMMENT types)
    max_score = models.DecimalField(
        max_digits=7, decimal_places=2, default=10,
        help_text="Maximum achievable score for this field.",
    )
    min_score = models.DecimalField(
        max_digits=7, decimal_places=2, default=0,
        help_text="Minimum score for this field (usually 0).",
    )

    # Options list for SELECT types (stored as JSON array of strings)
    options = models.JSONField(
        default=list, blank=True,
        help_text="List of option strings for SINGLE_SELECT or MULTI_SELECT fields.",
    )

    # Mode B — reviewer annotates an appraisee field
    reviewer_can_score = models.BooleanField(
        default=False,
        help_text="If True and filled_by=APPRAISEE, the designated reviewer can also give a score on this field."
    )
    reviewer_score_role = models.CharField(
        max_length=20,
        choices=FILLED_BY_CHOICES,
        blank=True,
        help_text="Which reviewer role provides the score (Mode B).",
    )
    reviewer_score_max = models.DecimalField(
        max_digits=7, decimal_places=2, default=10, blank=True,
        help_text="Maximum score the reviewer can give on this field (Mode B).",
    )
    reviewer_can_comment = models.BooleanField(
        default=False,
        help_text="If True and filled_by=APPRAISEE, the designated reviewer can add a comment on this field."
    )
    reviewer_comment_role = models.CharField(
        max_length=20,
        choices=FILLED_BY_CHOICES,
        blank=True,
        help_text="Which reviewer role provides the comment (Mode B).",
    )

    is_required = models.BooleanField(
        default=True,
        help_text="Whether this field must be filled before the form can be submitted.",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Form Field'
        verbose_name_plural = 'Form Fields'

    def __str__(self):
        return f"{self.label} [{self.get_field_type_display()}] — {self.section.name}"

    @property
    def is_scored(self):
        """True if this field produces a numeric score."""
        return self.field_type in (self.SCORE, self.SCORE_COMMENT)

    @property
    def is_select(self):
        return self.field_type in (self.SINGLE_SELECT, self.MULTI_SELECT)


class FormFieldResponse(models.Model):
    """
    Stores a single response to a single FormField for one Appraisal.

    The (appraisal, field, responded_by, response_type) combination is unique,
    which allows an appraisee AND a reviewer to independently respond to the
    same field (Mode B: reviewer scores/comments on an appraisee field).
    """

    PRIMARY          = 'PRIMARY'          # Normal field fill (appraisee or appraiser)
    REVIEWER_SCORE   = 'REVIEWER_SCORE'   # Mode B: reviewer's score on appraisee field
    REVIEWER_COMMENT = 'REVIEWER_COMMENT' # Mode B: reviewer's comment on appraisee field

    RESPONSE_TYPE_CHOICES = [
        (PRIMARY,          'Primary Response'),
        (REVIEWER_SCORE,   'Reviewer Score'),
        (REVIEWER_COMMENT, 'Reviewer Comment'),
    ]

    appraisal = models.ForeignKey(
        'Appraisal',
        on_delete=models.CASCADE,
        related_name='form_responses',
    )
    field = models.ForeignKey(
        FormField,
        on_delete=models.CASCADE,
        related_name='responses',
    )
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='form_field_responses',
    )
    response_type = models.CharField(
        max_length=20,
        choices=RESPONSE_TYPE_CHOICES,
        default=PRIMARY,
    )

    # Populated based on field_type
    text_response = models.TextField(
        blank=True,
        help_text="Response for NARRATIVE fields or the comment part of SCORE_COMMENT.",
    )
    score = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Numeric score for SCORE, SCORE_COMMENT, or reviewer Mode B score.",
    )
    selected_options = models.JSONField(
        default=list, blank=True,
        help_text="Selected option(s) for SINGLE_SELECT and MULTI_SELECT fields.",
    )
    evidence_file = models.FileField(
        upload_to='evidence/form_fields/',
        null=True, blank=True,
    )
    responded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('appraisal', 'field', 'responded_by', 'response_type')]
        ordering = ['field__order']
        verbose_name = 'Form Field Response'
        verbose_name_plural = 'Form Field Responses'

    def __str__(self):
        user = self.responded_by.get_full_name() if self.responded_by else 'Unknown'
        return f"{user} → {self.field.label} [{self.response_type}]"


# ============================================================
# APPRAISAL RECORD
# ============================================================

class Appraisal(models.Model):
    """
    A single staff member's appraisal within a given cycle.

    Tracks the full dynamic workflow from self-assessment through
    configurable multi-step approval, including all aggregate scores.

    The approval chain is driven by `override_process` (if set) or the
    cycle's general ApprovalProcess. `current_step_number` tracks which
    step is currently pending action.
    """

    # --- Status choices ---
    NOT_STARTED = 'NOT_STARTED'
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    AWAITING_STEP_REVIEW = 'AWAITING_STEP_REVIEW'
    RETURNED_TO_STAFF = 'RETURNED_TO_STAFF'
    RETURNED_TO_REVIEWER = 'RETURNED_TO_REVIEWER'
    APPROVED = 'APPROVED'
    STAFF_ACKNOWLEDGED = 'STAFF_ACKNOWLEDGED'
    ARCHIVED = 'ARCHIVED'

    # Legacy aliases (kept for backwards compatibility with old data)
    UNDER_REVIEW = 'AWAITING_STEP_REVIEW'
    REVIEWED = 'APPROVED'
    RETURNED_TO_SUPERVISOR = 'RETURNED_TO_REVIEWER'

    STATUS_CHOICES = [
        (NOT_STARTED, 'Not Started'),
        (DRAFT, 'Draft'),
        (SUBMITTED, 'Submitted — Awaiting Step 1'),
        (AWAITING_STEP_REVIEW, 'Awaiting Reviewer Action'),
        (RETURNED_TO_STAFF, 'Returned to Staff'),
        (RETURNED_TO_REVIEWER, 'Returned to Previous Reviewer'),
        (APPROVED, 'Fully Approved'),
        (STAFF_ACKNOWLEDGED, 'Staff Acknowledged'),
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

    # --- Dynamic approval workflow ---
    override_process = models.ForeignKey(
        ApprovalProcess,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='override_appraisals',
        help_text="If set, overrides the cycle's general approval process for this staff member."
    )
    current_step_number = models.PositiveIntegerField(
        default=0,
        help_text="0 = not yet submitted. 1+ = the step currently awaiting action."
    )

    # --- Legacy supervisor FK (kept for compatibility, now also used for step 1 auto-assign) ---
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_appraisals',
    )

    # --- Timestamps ---
    self_submitted_at = models.DateTimeField(null=True, blank=True)
    supervisor_reviewed_at = models.DateTimeField(null=True, blank=True)
    hod_reviewed_at = models.DateTimeField(null=True, blank=True)
    staff_acknowledged_at = models.DateTimeField(null=True, blank=True)

    # --- Scores ---
    overall_self_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    overall_supervisor_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    final_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )

    # --- Return notes ---
    supervisor_return_notes = models.TextField(
        blank=True,
        help_text="Reason provided when returning the appraisal to the staff."
    )
    hod_return_notes = models.TextField(
        blank=True,
        help_text="Reason provided by the HOD when returning the appraisal."
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

    # ------------------------------------------------------------------
    # Approval workflow helpers
    # ------------------------------------------------------------------

    @property
    def active_process(self):
        """Return the override process if set, else the cycle's general process."""
        if self.override_process_id:
            return self.override_process
        return self.cycle.general_approval_process

    @property
    def current_assignment(self):
        """Return the PENDING AppraisalApprovalAssignment for the current step."""
        if self.current_step_number == 0:
            return None
        return self.approval_assignments.filter(
            step__step_number=self.current_step_number,
            status=AppraisalApprovalAssignment.PENDING,
        ).select_related('step', 'approver').first()

    @property
    def total_steps(self):
        """Total number of steps in the active process."""
        process = self.active_process
        if process:
            return process.steps.count()
        return 0

    @property
    def progress_percent(self):
        """Percentage of approval steps completed (for progress bars)."""
        if self.status in [self.APPROVED, self.STAFF_ACKNOWLEDGED, self.ARCHIVED]:
            return 100
        if self.total_steps == 0 or self.current_step_number == 0:
            return 0
        return int(((self.current_step_number - 1) / self.total_steps) * 100)

    @property
    def has_supervisor_draft(self):
        """Returns True if the current step's approver has started reviewing."""
        if self.status not in [self.SUBMITTED, self.AWAITING_STEP_REVIEW]:
            return False
        if self.kpi_scores.filter(supervisor_score__isnull=False).exists():
            return True
        if self.competency_scores.filter(supervisor_score__isnull=False).exists():
            return True
        if hasattr(self, 'supervisor_review'):
            if self.supervisor_review.overall_comments or self.supervisor_review.recommendation:
                return True
        return False

    def get_assignment_for_step(self, step_number):
        """Return the assignment for a specific step number."""
        return self.approval_assignments.filter(
            step__step_number=step_number
        ).select_related('step', 'approver').first()


# ============================================================
# SCORES
# ============================================================

class KPIScore(models.Model):
    """
    Records the self and reviewer scores for a single KPI item
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
        max_digits=4, decimal_places=2, null=True, blank=True,
    )
    supervisor_score = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
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
    Records the self and reviewer scores for a single competency item
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
        max_digits=4, decimal_places=2, null=True, blank=True,
    )
    supervisor_score = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
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
    The first-step approver's qualitative review of a staff appraisal,
    including an overall recommendation and narrative feedback.
    Kept for backward compatibility and as a convenience record for step-1 data.
    """

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
    Head of Department review record (kept for backward compatibility).
    In the new dynamic workflow, HOD actions are tracked via AppraisalApprovalAssignment.
    """

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
        blank=True,
    )
    reviewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'HOD Review'
        verbose_name_plural = 'HOD Reviews'

    def __str__(self):
        return f"HOD Review for {self.appraisal}"


class NarrativeResponse(models.Model):
    """
    Staff or reviewer response to a NarrativeField.
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
        return f"Response to {self.field.name} for {self.appraisal.staff.get_full_name()}"
