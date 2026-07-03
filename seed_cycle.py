import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from appraisals.models import AppraisalCycle, NarrativeField, KPICategory, KPIItem, CompetencyCategory, CompetencyItem

def seed():
    # Create the cycle
    cycle, created = AppraisalCycle.objects.get_or_create(
        name="Annual Performance Appraisal (Hospital) 2025",
        defaults={
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
            'scoring_scale': 5,
            'status': AppraisalCycle.DRAFT
        }
    )
    if not created:
        print(f"Cycle '{cycle.name}' already exists. Updating it...")
        # Clear existing items for clean seed
        cycle.narrative_fields.all().delete()
        cycle.kpi_categories.all().delete()
        cycle.competency_categories.all().delete()
        
    print(f"Seeding Cycle: {cycle.name}")

    # --- Narrative Fields ---
    staff_fields = [
        "State below in order of importance KPIs and the main duties performed during period of report",
        "List the number of core job functions performed within the year under review",
        "Performance Challenge(s)",
        "Suggestions to remediate challenge(s)",
        "Other comments (Appraisee)"
    ]
    for i, name in enumerate(staff_fields):
        NarrativeField.objects.create(cycle=cycle, name=name, is_supervisor_field=False, order=i)
        
    sup_fields = [
        "Appraiser’s Comment(s)",
        "Areas for improvement/focus (Skills, Performance, Behavioral Gaps)",
        "Other comment(s) (Appraiser)",
        "Staff training need(s)",
        "1st Reviewing Supervisor’s Comment(s) (HOD)",
        "2nd Reviewing Supervisor’s Comment(s) (DIRECTOR)",
        "HOU Personnel Management’s Comment(s)"
    ]
    for i, name in enumerate(sup_fields):
        NarrativeField.objects.create(cycle=cycle, name=name, is_supervisor_field=True, order=len(staff_fields)+i)
        
    # --- KPIs ---
    kpi_cat = KPICategory.objects.create(cycle=cycle, name="Quantitative Appraisal (KPIs)", weight=100, order=1)
    kpis = [
        ("Revenue Target Achieved", 60),
        ("Number of Taxpayers brought to the net", 10),
        ("Number of Assessment Served", 25),
        ("Other Responsibility", 5)
    ]
    for i, (name, weight) in enumerate(kpis):
        KPIItem.objects.create(category=kpi_cat, name=name, weight=weight, order=i)

    # --- Competencies ---
    comp_cat = CompetencyCategory.objects.create(cycle=cycle, name="Qualitative Appraisal (Competencies)", weight=100, order=1)
    competencies = [
        "Punctuality/Attendance: Abide by resumption and close time.",
        "Job Knowledge: Possesses general and professional skills to perform the job",
        "Result oriented: Accomplish task while overcoming obstacles and making adjustment within a good turn-around time",
        "Communication Skills: Organize and express ideas clearly (both oral and written)",
        "Ethical Conduct: Work within laid down policy & procedure with highest professional standard.",
        "Creativity/Innovation: Ability to bring initiative, suggest better ways to improve processes",
        "Team Work: Provide complimentary skills that will create synergy for achieving group assignment",
        "Interpersonal Relations: Display empathy and high emotional intelligence. Approachable and respectable to others",
        "Quality: Completes tasks according to standard procedure with minimal supervision within set time",
        "Attention to Details: Thorough concern for all areas involved, no matter how small"
    ]
    # Distribute 100% weight evenly (10% each)
    for i, name in enumerate(competencies):
        CompetencyItem.objects.create(category=comp_cat, name=name, weight=10, order=i)

    print("Seed complete! You can view it in the HR Admin portal.")

if __name__ == '__main__':
    seed()
