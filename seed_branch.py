"""
Data seed script to create the default 'Headquarters' branch
and assign all existing users, departments, and cycle #3 to it.

Run with: python manage.py shell < seed_branch.py
"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from branches.models import Branch
from accounts.models import CustomUser
from departments.models import Department
from appraisals.models import AppraisalCycle

# Create the default branch
branch, created = Branch.objects.get_or_create(
    code='HQ',
    defaults={
        'name': 'Headquarters',
        'description': 'Main office / headquarters of the State Internal Revenue Service.',
    }
)
print(f"{'Created' if created else 'Found'} branch: {branch.name} ({branch.code})")

# Assign ALL existing users to this branch
all_users = CustomUser.objects.all()
branch.members.set(all_users)
print(f"Assigned {all_users.count()} users to {branch.name}")

# Assign ALL existing departments to this branch
all_depts = Department.objects.all()
branch.departments.set(all_depts)
print(f"Assigned {all_depts.count()} departments to {branch.name}")

# Link existing cycles to this branch
cycles_updated = AppraisalCycle.objects.filter(branch__isnull=True).update(branch=branch)
print(f"Linked {cycles_updated} cycle(s) to {branch.name}")

print("\nDone! Default branch setup complete.")
