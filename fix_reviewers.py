import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from appraisals.models import AppraisalReturnLog
from accounts.models import CustomUser

logs = AppraisalReturnLog.objects.filter(reviewer__isnull=True)
updated = 0

for log in logs:
    appraisal = log.appraisal
    if log.from_step_number == 1:
        log.reviewer = appraisal.staff.supervisor
        log.save()
        updated += 1
    elif log.from_step_number == 2:
        # Find HOD for the department
        hod = CustomUser.objects.filter(department=appraisal.staff.department, role=CustomUser.HOD).first()
        if hod:
            log.reviewer = hod
            log.save()
            updated += 1

print(f"Updated {updated} return logs with reviewer information.")
