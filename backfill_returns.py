import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from appraisals.models import Appraisal, AppraisalReturnLog, AppraisalApprovalAssignment

appraisals_with_notes = Appraisal.objects.exclude(supervisor_return_notes='').exclude(supervisor_return_notes__isnull=True) | Appraisal.objects.exclude(hod_return_notes='').exclude(hod_return_notes__isnull=True)
appraisals_with_notes = appraisals_with_notes.distinct()

created_count = 0

for appraisal in appraisals_with_notes:
    if appraisal.supervisor_return_notes:
        exists = AppraisalReturnLog.objects.filter(
            appraisal=appraisal,
            reason=appraisal.supervisor_return_notes
        ).exists()
        if not exists:
            AppraisalReturnLog.objects.create(
                appraisal=appraisal,
                reviewer=None,
                step=None,
                from_step_number=1,
                to_step_number=0,
                reason=appraisal.supervisor_return_notes,
                returned_at=appraisal.updated_at
            )
            created_count += 1
            
    if appraisal.hod_return_notes:
        exists = AppraisalReturnLog.objects.filter(
            appraisal=appraisal,
            reason=appraisal.hod_return_notes
        ).exists()
        if not exists:
            AppraisalReturnLog.objects.create(
                appraisal=appraisal,
                reviewer=None,
                step=None,
                from_step_number=2,
                to_step_number=1,
                reason=appraisal.hod_return_notes,
                returned_at=appraisal.updated_at
            )
            created_count += 1

print(f"Successfully migrated {created_count} past return records from Appraisal fields into the new log system.")
