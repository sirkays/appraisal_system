from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from departments.models import Department
from appraisals.models import AppraisalCycle, KPICategory, KPIItem, CompetencyCategory, CompetencyItem

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds initial departments and users for testing the appraisal system'

    def handle(self, *args, **options):
        self.stdout.write('Seeding initial data...')

        # Clear existing test users to avoid unique constraint issues
        User.objects.filter(username__in=['hod_tax', 'sup_tax', 'staff_tax']).delete()

        # 1. Update existing admin user role to HR_ADMIN
        admin_user = User.objects.filter(username='admin').first()
        if admin_user:
            admin_user.role = User.HR_ADMIN
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Updated admin user role to HR_ADMIN'))
        else:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@revenue.gov.ng',
                password='adminpassword123',
                role=User.HR_ADMIN
            )
            self.stdout.write(self.style.SUCCESS('Created admin user with HR_ADMIN role'))

        # 2. Create Departments
        tax_dept, created = Department.objects.get_or_create(
            code='TAX',
            defaults={'name': 'Taxation Department', 'description': 'Responsible for tax collection and assessment.'}
        )
        if created:
            self.stdout.write(f"Created Department: {tax_dept.name}")

        audit_dept, created = Department.objects.get_or_create(
            code='AUDIT',
            defaults={'name': 'Audit & Investigation', 'description': 'Responsible for tax audits and investigations.'}
        )
        if created:
            self.stdout.write(f"Created Department: {audit_dept.name}")

        hr_dept, created = Department.objects.get_or_create(
            code='HR',
            defaults={'name': 'Human Resources', 'description': 'Manages staff welfare, appraisals, and recruitment.'}
        )
        if created:
            self.stdout.write(f"Created Department: {hr_dept.name}")

        # 3. Create HOD User
        hod_tax, created = User.objects.get_or_create(
            username='hod_tax',
            defaults={
                'email': 'hod.tax@revenue.gov.ng',
                'first_name': 'Tunde',
                'last_name': 'Bello',
                'role': User.HOD,
                'department': tax_dept,
                'designation': 'Head of Taxation'
            }
        )
        if created:
            hod_tax.set_password('pass123')
            hod_tax.save()
            self.stdout.write(self.style.SUCCESS(f"Created HOD: {hod_tax.get_full_name()} ({hod_tax.staff_id})"))

        # Link HOD as head of Taxation department
        if tax_dept.hod != hod_tax:
            tax_dept.hod = hod_tax
            tax_dept.save()
            self.stdout.write(self.style.SUCCESS(f"Assigned {hod_tax.get_full_name()} as HOD of Taxation"))

        # 4. Create Supervisor User
        sup_tax, created = User.objects.get_or_create(
            username='sup_tax',
            defaults={
                'email': 'sup.tax@revenue.gov.ng',
                'first_name': 'Sarah',
                'last_name': 'Okon',
                'role': User.SUPERVISOR,
                'department': tax_dept,
                'designation': 'Tax Supervisor',
                'supervisor': hod_tax
            }
        )
        if created:
            sup_tax.set_password('pass123')
            sup_tax.save()
            self.stdout.write(self.style.SUCCESS(f"Created Supervisor: {sup_tax.get_full_name()} ({sup_tax.staff_id})"))

        # 5. Create Staff User
        staff_tax, created = User.objects.get_or_create(
            username='staff_tax',
            defaults={
                'email': 'staff.tax@revenue.gov.ng',
                'first_name': 'John',
                'last_name': 'Nwachukwu',
                'role': User.STAFF,
                'department': tax_dept,
                'designation': 'Tax Officer II',
                'supervisor': sup_tax
            }
        )
        if created:
            staff_tax.set_password('pass123')
            staff_tax.save()
            self.stdout.write(self.style.SUCCESS(f"Created Staff: {staff_tax.get_full_name()} ({staff_tax.staff_id})"))

        # 6. Create Active Appraisal Cycle
        cycle, created = AppraisalCycle.objects.get_or_create(
            name="2026 Q3 Review",
            defaults={
                'frequency': AppraisalCycle.QUARTERLY,
                'start_date': date(2026, 7, 1),
                'end_date': date(2026, 9, 30),
                'status': AppraisalCycle.ACTIVE,
                'scoring_scale': 5,
                'created_by': admin_user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Active Cycle: {cycle.name}"))
        else:
            # Enforce status is ACTIVE for testing
            cycle.status = AppraisalCycle.ACTIVE
            cycle.save()

        # 7. Create KPI Categories & Items
        kpi_cat1, _ = KPICategory.objects.get_or_create(
            name="Revenue Collection & Assessment",
            cycle=cycle,
            defaults={'weight': 50.00, 'order': 1, 'description': 'Responsible for tax collection and assessment metrics.'}
        )
        KPIItem.objects.get_or_create(
            category=kpi_cat1,
            name="Revenue Target Achievement",
            defaults={'weight': 50.00, 'order': 1, 'description': 'Achieve target collection of revenue as assigned for the quarter.'}
        )
        KPIItem.objects.get_or_create(
            category=kpi_cat1,
            name="Assessment Accuracy & Timeliness",
            defaults={'weight': 50.00, 'order': 2, 'description': 'Ensure taxpayer assessments are accurate, compliant, and completed on schedule.'}
        )

        kpi_cat2, _ = KPICategory.objects.get_or_create(
            name="Customer Service & Taxpayer Relations",
            cycle=cycle,
            defaults={'weight': 30.00, 'order': 2, 'description': 'Responsible for managing taxpayer queries and education.'}
        )
        KPIItem.objects.get_or_create(
            category=kpi_cat2,
            name="Taxpayer Query Resolution",
            defaults={'weight': 50.00, 'order': 1, 'description': 'Resolve complaints and general queries within the standard SLA window.'}
        )
        KPIItem.objects.get_or_create(
            category=kpi_cat2,
            name="Taxpayer Awareness Campaigns",
            defaults={'weight': 50.00, 'order': 2, 'description': 'Conduct or support public tax education and outreach initiatives.'}
        )

        kpi_cat3, _ = KPICategory.objects.get_or_create(
            name="Process Efficiency & Reporting",
            cycle=cycle,
            defaults={'weight': 20.00, 'order': 3, 'description': 'Timely and efficient reporting.'}
        )
        KPIItem.objects.get_or_create(
            category=kpi_cat3,
            name="Report Submission",
            defaults={'weight': 100.00, 'order': 1, 'description': 'Preparation and submission of standard weekly, monthly, and quarterly performance reports.'}
        )

        # 8. Create Competency Categories & Items
        comp_cat1, _ = CompetencyCategory.objects.get_or_create(
            name="Core Professional Competencies",
            cycle=cycle,
            defaults={'weight': 60.00, 'order': 1, 'description': 'Professional and technical capabilities.'}
        )
        CompetencyItem.objects.get_or_create(
            category=comp_cat1,
            name="Professionalism & Integrity",
            defaults={'weight': 34.00, 'order': 1, 'description': 'Adherence to ethical standards, transparency, and civil service code.'}
        )
        CompetencyItem.objects.get_or_create(
            category=comp_cat1,
            name="Technical Knowledge of Tax Laws",
            defaults={'weight': 33.00, 'order': 2, 'description': 'Proficiency in applying relevant tax laws, protocols, and IT tax systems.'}
        )
        CompetencyItem.objects.get_or_create(
            category=comp_cat1,
            name="Communication & Stakeholder Management",
            defaults={'weight': 33.00, 'order': 3, 'description': 'Effectiveness in conveying instructions and handling taxpayer communications.'}
        )

        comp_cat2, _ = CompetencyCategory.objects.get_or_create(
            name="Behavioral Competencies",
            cycle=cycle,
            defaults={'weight': 40.00, 'order': 2, 'description': 'Behavioral and interpersonal skills.'}
        )
        CompetencyItem.objects.get_or_create(
            category=comp_cat2,
            name="Teamwork & Collaboration",
            defaults={'weight': 50.00, 'order': 1, 'description': 'Working constructively within and across teams to achieve goals.'}
        )
        CompetencyItem.objects.get_or_create(
            category=comp_cat2,
            name="Problem Solving & Adaptability",
            defaults={'weight': 50.00, 'order': 2, 'description': 'Responding effectively to process changes and resolving operational challenges.'}
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded all initial demo data including active Appraisal Cycle, KPIs, and Competencies.'))
