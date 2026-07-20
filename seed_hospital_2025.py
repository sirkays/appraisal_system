"""
Seed the 'Annual Performance Appraisal (Hospital) 2025' cycle
with all sections and fields from the sample appraisal form.

Run with:
    python seed_hospital_2025.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from appraisals.models import AppraisalCycle, ApprovalProcess, FormSection, FormField
from branches.models import Branch
from accounts.models import CustomUser

print("Seeding Hospital 2025 appraisal cycle...")

# --- Find or create the cycle ---
branch = Branch.objects.filter(name__icontains='Head').first() or Branch.objects.first()
hr_user = CustomUser.objects.filter(role=CustomUser.HR_ADMIN).first()

cycle, created = AppraisalCycle.objects.get_or_create(
    name='Annual Performance Appraisal (Hospital) 2025',
    defaults={
        'frequency': AppraisalCycle.ANNUAL,
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'status': AppraisalCycle.ACTIVE,
        'scoring_scale': 5,
        'branch': branch,
        'created_by': hr_user,
    }
)

if not created:
    print(f"  Cycle already exists (ID={cycle.id}), clearing existing form sections...")
    cycle.form_sections.all().delete()

print(f"  Cycle: {cycle.name} (ID={cycle.id}, Status={cycle.status})")

# ============================================================
# SECTION A — To Be Completed by Appraisee
# ============================================================
sec_a = FormSection.objects.create(
    cycle=cycle,
    name='Section A: To Be Completed by Appraisee',
    description='Complete all fields below before submitting your appraisal.',
    section_weight=0,  # Narrative only — no numeric score
    order=0,
)

appraisee_fields = [
    {
        'label': 'Key Performance Indicators (KPIs)',
        'description': 'State below in order of importance, your KPIs and the main duties performed during the period of report.',
        'field_type': FormField.NARRATIVE,
    },
    {
        'label': 'Performance Record — Core Job Functions',
        'description': 'List the number of core job functions performed within the year under review.',
        'field_type': FormField.NARRATIVE,
    },
    {
        'label': 'Performance Challenge(s)',
        'description': 'List any challenges you faced in performing your duties during the period.',
        'field_type': FormField.NARRATIVE,
    },
    {
        'label': 'Suggestions to Remediate Challenge(s)',
        'description': 'Suggest ways to address the challenges you listed above.',
        'field_type': FormField.NARRATIVE,
    },
    {
        'label': 'Other Comments',
        'description': 'Any other comments you wish to add.',
        'field_type': FormField.NARRATIVE,
        'is_required': False,
    },
]

for i, f in enumerate(appraisee_fields):
    FormField.objects.create(
        section=sec_a,
        label=f['label'],
        description=f.get('description', ''),
        field_type=f.get('field_type', FormField.NARRATIVE),
        filled_by=FormField.APPRAISEE,
        is_required=f.get('is_required', True),
        order=i,
    )

print(f"  Section A created with {len(appraisee_fields)} fields")

# ============================================================
# SECTION B — Quantitative Appraisal (Appraiser)
# ============================================================
sec_b = FormSection.objects.create(
    cycle=cycle,
    name='Section B: Quantitative Appraisal',
    description='To be completed by the appraiser. Enter the score obtained for each KPI.',
    section_weight=50,  # 50% of total score
    order=1,
)

quant_fields = [
    ('Revenue Target Achieved', 60),
    ('Number of Taxpayers Brought to the Net', 10),
    ('Number of Assessment Served', 25),
    ('Other Responsibility', 5),
]

for i, (label, max_score) in enumerate(quant_fields):
    FormField.objects.create(
        section=sec_b,
        label=label,
        description=f'Maximum score obtainable: {max_score}',
        field_type=FormField.SCORE,
        filled_by=FormField.SUPERVISOR,
        max_score=max_score,
        min_score=0,
        is_required=True,
        order=i,
    )

print(f"  Section B created with {len(quant_fields)} fields (total max = 100)")

# ============================================================
# SECTION C — Qualitative Appraisal (Appraiser)
# ============================================================
sec_c = FormSection.objects.create(
    cycle=cycle,
    name='Section C: Qualitative Appraisal',
    description='To be completed by the appraiser. Score each competency (max 5 per item, total max 50).',
    section_weight=50,  # 50% of total score
    order=2,
)

qual_fields = [
    ('Punctuality/Attendance', 'Abide by resumption and close time.'),
    ('Job Knowledge', 'Possesses general and professional skills to perform the job.'),
    ('Result Oriented', 'Accomplishes tasks while overcoming obstacles and making adjustments within a good turn-around time.'),
    ('Communication Skills', 'Organizes and expresses ideas clearly (both oral and written).'),
    ('Ethical Conduct', 'Works within laid down policy & procedure with highest professional standard.'),
    ('Creativity/Innovation', 'Ability to bring initiative, suggest better ways to improve processes.'),
    ('Team Work', 'Provides complementary skills that will create synergy for achieving group assignment.'),
    ('Interpersonal Relations', 'Displays empathy and high emotional intelligence. Approachable and respectable to others.'),
    ('Quality', 'Completes tasks according to standard procedure with minimal supervision within set time.'),
    ('Attention to Details', 'Thorough concern for all areas involved, no matter how small.'),
]

for i, (label, desc) in enumerate(qual_fields):
    FormField.objects.create(
        section=sec_c,
        label=label,
        description=desc,
        field_type=FormField.SCORE,
        filled_by=FormField.SUPERVISOR,
        max_score=5,
        min_score=1,
        is_required=True,
        order=i,
    )

print(f"  Section C created with {len(qual_fields)} fields (max 5 each = total 50)")

# ============================================================
# SECTION D — Appraiser Comments
# ============================================================
sec_d = FormSection.objects.create(
    cycle=cycle,
    name='Section D: Appraiser Comments',
    description='To be completed by the appraiser (Supervisor/First Reviewer).',
    section_weight=0,
    order=3,
)

appraiser_comment_fields = [
    ("Appraiser's Comment(s)", "General comments on the staff's performance."),
    ("Areas for Improvement/Focus", "Skills, Performance, and Behavioral Gaps identified."),
    ("Other Comment(s)", "Any other comments from the appraiser.", False),
    ("Staff Training Need(s)", "Training programs or development areas recommended for the staff."),
]

for i, entry in enumerate(appraiser_comment_fields):
    label, desc = entry[0], entry[1]
    required = entry[2] if len(entry) > 2 else True
    FormField.objects.create(
        section=sec_d,
        label=label,
        description=desc,
        field_type=FormField.NARRATIVE,
        filled_by=FormField.SUPERVISOR,
        is_required=required,
        order=i,
    )

print(f"  Section D created with {len(appraiser_comment_fields)} fields")

# ============================================================
# SECTION E — Second Level Appraiser (HOD)
# ============================================================
sec_e = FormSection.objects.create(
    cycle=cycle,
    name='Section E: Second Level Appraiser (HOD)',
    description="1st Reviewing Supervisor's Comments (Head of Department).",
    section_weight=0,
    order=4,
)

FormField.objects.create(
    section=sec_e,
    label="HOD Review Comments",
    description="1st Reviewing Supervisor's Comment(s) — Head of Department.",
    field_type=FormField.NARRATIVE,
    filled_by=FormField.HOD,
    is_required=True,
    order=0,
)

print("  Section E created with 1 field (HOD)")

# ============================================================
# SECTION F — Third Level Appraiser (Director)
# ============================================================
sec_f = FormSection.objects.create(
    cycle=cycle,
    name='Section F: Third Level Appraiser (Director)',
    description="2nd Reviewing Supervisor's Comments (Director/Executive).",
    section_weight=0,
    order=5,
)

FormField.objects.create(
    section=sec_f,
    label="Director Review Comments",
    description="2nd Reviewing Supervisor's Comment(s) — Director/Executive.",
    field_type=FormField.NARRATIVE,
    filled_by=FormField.DIRECTORATE,
    is_required=True,
    order=0,
)

print("  Section F created with 1 field (Director)")

# ============================================================
# SECTION G — HR Personnel Management
# ============================================================
sec_g = FormSection.objects.create(
    cycle=cycle,
    name='Section G: HR Personnel Management',
    description="HOU Personnel Management's Comments.",
    section_weight=0,
    order=6,
)

FormField.objects.create(
    section=sec_g,
    label="HR Personnel Comment(s)",
    description="HOU Personnel Management's Comment(s) and remarks.",
    field_type=FormField.NARRATIVE,
    filled_by=FormField.HR_ADMIN,
    is_required=False,
    order=0,
)

print("  Section G created with 1 field (HR Admin)")

print()
print(f"✅ Seeding complete!")
print(f"   Cycle: {cycle.name}")
print(f"   Sections: {cycle.form_sections.count()}")
total_fields = sum(s.fields.count() for s in cycle.form_sections.all())
print(f"   Total Fields: {total_fields}")
print(f"   Status: {cycle.status}")
