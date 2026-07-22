import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import CustomUser
from appraisals.models import AppraisalApprovalAssignment

for user in CustomUser.objects.all():
    count = AppraisalApprovalAssignment.objects.filter(approver=user).exclude(status='PENDING').count()
    if count > 0:
        print(f"User {user.username} ({user.staff_id}) has {count} past assignments.")
