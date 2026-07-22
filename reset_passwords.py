"""
Reset all user passwords to 'pass123'.
Usage: python manage.py shell < reset_passwords.py
"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import CustomUser

users = CustomUser.objects.all()
count = 0

for user in users:
    user.set_password('pass123')
    user.save(update_fields=['password'])
    count += 1
    print(f"  ✓ {user.username} ({user.staff_id})")

print(f"\nDone. Reset {count} user passwords to 'pass123'.")
