"""
Management command to seed demo accounts and test data.

Creates:
- Taxation department
- 5 demo users (admin, HOD, Supervisor, Staff, Director)
- Proper supervisor/department linkages
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from departments.models import Department

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds demo accounts and test data for the appraisal system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding demo accounts..."))

        # ── 1. Create Taxation Department (placeholder HOD — will update after users) ──
        dept, dept_created = Department.objects.get_or_create(
            code='TAX',
            defaults={
                'name': 'Taxation',
                'description': 'Handles all taxation and revenue assessment activities.',
            }
        )
        if dept_created:
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created department: {dept.name}"))
        else:
            self.stdout.write(f"  [--] Department '{dept.name}' already exists.")

        # -- 2. HR Administrator --
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@revenue.gov.ng',
                'first_name': 'HR',
                'last_name': 'Administrator',
                'role': User.HR_ADMIN,
                'designation': 'HR Administrator',
                'is_staff': True,
            }
        )
        if created:
            admin_user.set_password('adminpassword123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created HR Admin: {admin_user.username}"))
        else:
            self.stdout.write(f"  [--] User '{admin_user.username}' already exists.")

        # -- 3. Director of Revenue Operations --
        director, created = User.objects.get_or_create(
            username='dir_revenue',
            defaults={
                'email': 'director.revenue@revenue.gov.ng',
                'first_name': 'Director',
                'last_name': 'Revenue',
                'role': User.DIRECTORATE,
                'designation': 'Director of Revenue Operations',
                'department': dept,
            }
        )
        if created:
            director.set_password('pass123')
            director.save()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created Director: {director.username}"))
        else:
            self.stdout.write(f"  [--] User '{director.username}' already exists.")

        # -- 4. Head of Department (HOD) --
        hod, created = User.objects.get_or_create(
            username='hod_tax',
            defaults={
                'email': 'hod.tax@revenue.gov.ng',
                'first_name': 'John',
                'last_name': 'Adewale',
                'role': User.HOD,
                'designation': 'Head of Taxation',
                'department': dept,
            }
        )
        if created:
            hod.set_password('pass123')
            hod.save()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created HOD: {hod.username}"))
        else:
            self.stdout.write(f"  [--] User '{hod.username}' already exists.")

        # Link HOD to department
        if dept.hod != hod:
            dept.hod = hod
            dept.save()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Linked {hod.get_full_name()} as HOD of {dept.name}"))

        # -- 5. Supervisor --
        supervisor, created = User.objects.get_or_create(
            username='sup_tax',
            defaults={
                'email': 'sup.tax@revenue.gov.ng',
                'first_name': 'Aminu',
                'last_name': 'Bello',
                'role': User.SUPERVISOR,
                'designation': 'Tax Supervisor',
                'department': dept,
                'supervisor': hod,
            }
        )
        if created:
            supervisor.set_password('pass123')
            supervisor.save()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created Supervisor: {supervisor.username}"))
        else:
            self.stdout.write(f"  [--] User '{supervisor.username}' already exists.")

        # -- 6. Staff Officer --
        staff, created = User.objects.get_or_create(
            username='staff_tax',
            defaults={
                'email': 'staff.tax@revenue.gov.ng',
                'first_name': 'Fatima',
                'last_name': 'Okonkwo',
                'role': User.STAFF,
                'designation': 'Tax Officer II',
                'department': dept,
                'supervisor': supervisor,
            }
        )
        if created:
            staff.set_password('pass123')
            staff.save()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created Staff: {staff.username}"))
        else:
            self.stdout.write(f"  [--] User '{staff.username}' already exists.")

        # -- Summary --
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("Demo accounts seeded successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("")
        self.stdout.write("Login credentials:")
        credentials = [
            ("HR Administrator", "admin", "adminpassword123"),
            ("Director", "dir_revenue", "pass123"),
            ("HOD (Taxation)", "hod_tax", "pass123"),
            ("Supervisor", "sup_tax", "pass123"),
            ("Staff Officer", "staff_tax", "pass123"),
        ]
        for role, username, password in credentials:
            self.stdout.write(f"  {role:20s} => username: {username:15s} | password: {password}")
        self.stdout.write("")
