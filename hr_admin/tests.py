from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
import json

from accounts.models import CustomUser
from appraisals.models import (
    Appraisal,
    AppraisalApprovalAssignment,
    AppraisalCycle,
    ApprovalProcess,
    ApprovalStep,
    FormField,
    FormSection,
)
from branches.models import Branch
from departments.models import Department


class StaffDirectoryFilterTests(TestCase):
    def setUp(self):
        self.hr = CustomUser.objects.create_user(
            username="hr_admin",
            password="pass12345",
            staff_id="HR-001",
            role=CustomUser.HR_ADMIN,
        )
        self.tax_department = Department.objects.create(name="Taxation", code="TAX")
        self.audit_department = Department.objects.create(name="Audit", code="AUD")
        self.hq_branch = Branch.objects.create(name="Headquarters", code="HQ")
        self.zonal_branch = Branch.objects.create(name="Zonal Office", code="ZO")
        self.hq_branch.departments.add(self.tax_department)
        self.zonal_branch.departments.add(self.audit_department)

        self.tax_staff = CustomUser.objects.create_user(
            username="tax_staff",
            password="pass12345",
            staff_id="STF-001",
            role=CustomUser.STAFF,
            department=self.tax_department,
            first_name="Tax",
            last_name="Staff",
        )
        self.audit_staff = CustomUser.objects.create_user(
            username="audit_staff",
            password="pass12345",
            staff_id="STF-002",
            role=CustomUser.SUPERVISOR,
            department=self.audit_department,
            first_name="Audit",
            last_name="Supervisor",
        )
        self.hq_branch.members.add(self.tax_staff)
        self.zonal_branch.members.add(self.audit_staff)

        self.cycle = AppraisalCycle.objects.create(
            name="Annual Review",
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            created_by=self.hr,
        )
        Appraisal.objects.create(
            cycle=self.cycle,
            staff=self.tax_staff,
            status=Appraisal.SUBMITTED,
        )

    def test_staff_directory_defaults_to_all_branches_and_active_cycle_statuses(self):
        self.client.login(username="hr_admin", password="pass12345")

        response = self.client.get(reverse("hr_admin:staff_list"))

        self.assertContains(response, "All branches")
        self.assertContains(response, "Tax Staff")
        self.assertContains(response, "Audit Supervisor")
        self.assertContains(response, "Submitted — Awaiting Step 1")
        self.assertContains(response, "No record")
        self.assertEqual(response.context["selected_cycle"], self.cycle)

    def test_staff_directory_filters_by_branch_role_and_appraisal_status(self):
        self.client.login(username="hr_admin", password="pass12345")

        response = self.client.get(
            reverse("hr_admin:staff_list"),
            {
                "branch": str(self.hq_branch.id),
                "role": CustomUser.STAFF,
                "cycle": str(self.cycle.id),
                "status": Appraisal.SUBMITTED,
            },
        )

        self.assertContains(response, "Tax Staff")
        self.assertNotContains(response, "Audit Supervisor")
        self.assertEqual(response.context["selected_branch_id"], str(self.hq_branch.id))
        self.assertEqual(response.context["selected_role"], CustomUser.STAFF)
        self.assertEqual(response.context["selected_status"], Appraisal.SUBMITTED)

    def test_hr_reviewer_can_access_review_queue_from_dashboard_sidebar(self):
        process = ApprovalProcess.objects.create(
            cycle=self.cycle,
            name="HR Review Process",
            is_general=True,
            created_by=self.hr,
        )
        step = ApprovalStep.objects.create(
            process=process,
            step_number=1,
            label="HR Review",
            role_required=ApprovalStep.HR_ADMIN,
        )
        appraisal = Appraisal.objects.get(cycle=self.cycle, staff=self.tax_staff)
        appraisal.current_step_number = 1
        appraisal.save(update_fields=["current_step_number"])
        AppraisalApprovalAssignment.objects.create(
            appraisal=appraisal,
            step=step,
            approver=self.hr,
            status=AppraisalApprovalAssignment.PENDING,
        )

        self.client.login(username="hr_admin", password="pass12345")
        response = self.client.get(reverse("hr_admin:dashboard"))

        self.assertContains(response, "My Review Queue")
        self.assertContains(response, "Awaiting My Review")
        self.assertContains(response, "Open review queue")
        self.assertEqual(response.context["awaiting_my_review"], 1)


class AppraisalCycleCloneTests(TestCase):
    def setUp(self):
        self.hr = CustomUser.objects.create_user(
            username="clone_hr_admin",
            password="pass12345",
            staff_id="HR-CLONE-001",
            role=CustomUser.HR_ADMIN,
        )
        self.department = Department.objects.create(name="Operations", code="OPS")
        self.staff = CustomUser.objects.create_user(
            username="clone_staff",
            password="pass12345",
            staff_id="CLONE-STF-001",
            role=CustomUser.STAFF,
            department=self.department,
        )
        self.cycle = AppraisalCycle.objects.create(
            name="Original Cycle",
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            scoring_scale=5,
            created_by=self.hr,
        )
        self.cycle.target_departments.add(self.department)
        self.cycle.target_staff.add(self.staff)
        section = FormSection.objects.create(
            cycle=self.cycle,
            name="Section A",
            description="Original instructions",
            section_weight=50,
            order=1,
        )
        FormField.objects.create(
            section=section,
            label="KPI completed",
            description="Maximum score obtainable: 10",
            field_type=FormField.SCORE,
            filled_by=FormField.SUPERVISOR,
            max_score=10,
            order=1,
        )
        process = ApprovalProcess.objects.create(
            cycle=self.cycle,
            name="Standard Review",
            is_general=True,
            created_by=self.hr,
        )
        ApprovalStep.objects.create(
            process=process,
            step_number=1,
            label="Supervisor Review",
            role_required=ApprovalStep.SUPERVISOR,
        )

    def test_hr_can_clone_cycle_setup_and_create_fresh_target_appraisals(self):
        self.client.login(username="clone_hr_admin", password="pass12345")

        response = self.client.post(reverse("hr_admin:cycle_clone", args=[self.cycle.id]))

        cloned = AppraisalCycle.objects.exclude(id=self.cycle.id).get()
        self.assertRedirects(response, reverse("hr_admin:cycle_edit", args=[cloned.id]))
        self.assertEqual(cloned.name, "Copy of Original Cycle")
        self.assertEqual(cloned.status, AppraisalCycle.DRAFT)
        self.assertEqual(cloned.form_sections.count(), 1)
        self.assertEqual(cloned.form_sections.first().fields.count(), 1)
        self.assertEqual(cloned.approval_processes.count(), 1)
        self.assertEqual(cloned.approval_processes.first().steps.count(), 1)
        self.assertIn(self.department, cloned.target_departments.all())
        self.assertIn(self.staff, cloned.target_staff.all())
        cloned_appraisal = Appraisal.objects.get(cycle=cloned, staff=self.staff)
        self.assertEqual(cloned_appraisal.status, Appraisal.NOT_STARTED)
        self.assertEqual(cloned_appraisal.approval_assignments.count(), 1)


class AppraisalCycleLifecycleTests(TestCase):
    def setUp(self):
        self.hr = CustomUser.objects.create_user(
            username="cycle_lifecycle_hr",
            password="pass12345",
            staff_id="LIFE-HR-001",
            role=CustomUser.HR_ADMIN,
        )
        self.staff = CustomUser.objects.create_user(
            username="cycle_lifecycle_staff",
            password="pass12345",
            staff_id="LIFE-STF-001",
            role=CustomUser.STAFF,
        )

    def make_cycle(self, name="Lifecycle Cycle"):
        return AppraisalCycle.objects.create(
            name=name,
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            created_by=self.hr,
        )

    def test_cycle_without_submitted_appraisals_can_be_deleted(self):
        cycle = self.make_cycle()
        Appraisal.objects.create(cycle=cycle, staff=self.staff, status=Appraisal.NOT_STARTED)
        self.client.login(username="cycle_lifecycle_hr", password="pass12345")

        response = self.client.post(reverse("hr_admin:cycle_delete", args=[cycle.id]))

        self.assertRedirects(response, reverse("hr_admin:cycle_list"))
        self.assertFalse(AppraisalCycle.objects.filter(id=cycle.id).exists())

    def test_cycle_with_submitted_appraisals_is_archived_first(self):
        cycle = self.make_cycle()
        Appraisal.objects.create(cycle=cycle, staff=self.staff, status=Appraisal.SUBMITTED)
        self.client.login(username="cycle_lifecycle_hr", password="pass12345")

        response = self.client.post(reverse("hr_admin:cycle_delete", args=[cycle.id]))

        self.assertRedirects(response, reverse("hr_admin:cycle_list"))
        cycle.refresh_from_db()
        self.assertEqual(cycle.status, AppraisalCycle.ARCHIVED)
        self.assertIsNotNone(cycle.archived_at)

    def test_archived_submitted_cycle_can_be_deleted_after_30_days(self):
        cycle = self.make_cycle()
        cycle.status = AppraisalCycle.ARCHIVED
        cycle.archived_at = timezone.now() - timedelta(days=31)
        cycle.save(update_fields=["status", "archived_at"])
        Appraisal.objects.create(cycle=cycle, staff=self.staff, status=Appraisal.SUBMITTED)
        self.client.login(username="cycle_lifecycle_hr", password="pass12345")

        response = self.client.post(reverse("hr_admin:cycle_delete", args=[cycle.id]))

        self.assertRedirects(response, reverse("hr_admin:cycle_list"))
        self.assertFalse(AppraisalCycle.objects.filter(id=cycle.id).exists())


class BulkApproverAssignmentTests(TestCase):
    def setUp(self):
        self.hr = CustomUser.objects.create_user(
            username="bulk_hr_admin",
            password="pass12345",
            staff_id="BULK-HR-001",
            role=CustomUser.HR_ADMIN,
        )
        self.director = CustomUser.objects.create_user(
            username="bulk_director",
            password="pass12345",
            staff_id="BULK-DIR-001",
            role=CustomUser.DIRECTORATE,
            first_name="Director",
            last_name="Audit",
        )
        self.department = Department.objects.create(name="Audit & Investigation", code="BAUD")
        self.branch = Branch.objects.create(name="Headquarters Bulk", code="BHQ")
        self.branch.departments.add(self.department)
        self.hod = CustomUser.objects.create_user(
            username="bulk_hod",
            password="pass12345",
            staff_id="BULK-HOD-001",
            role=CustomUser.HOD,
            first_name="HOD",
            last_name="Audit",
            department=self.department,
            supervisor=self.director,
        )
        self.department.hod = self.hod
        self.department.save(update_fields=["hod"])
        self.supervisor = CustomUser.objects.create_user(
            username="bulk_supervisor",
            password="pass12345",
            staff_id="BULK-SUP-001",
            role=CustomUser.SUPERVISOR,
            first_name="Supervisor",
            last_name="Audit",
            department=self.department,
            supervisor=self.hod,
        )
        self.staff = CustomUser.objects.create_user(
            username="bulk_staff",
            password="pass12345",
            staff_id="BULK-STF-001",
            role=CustomUser.STAFF,
            department=self.department,
            supervisor=self.supervisor,
        )
        self.cycle = AppraisalCycle.objects.create(
            name="Audit Cycle",
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            created_by=self.hr,
            branch=self.branch,
        )
        self.cycle.target_departments.add(self.department)
        self.branch.members.add(self.hr, self.supervisor, self.staff)
        self.branch_only_staff = CustomUser.objects.create_user(
            username="bulk_branch_only",
            password="pass12345",
            staff_id="BULK-BRN-001",
            role=CustomUser.HOD,
            first_name="Branch",
            last_name="Only",
        )
        self.branch.members.add(self.branch_only_staff)
        process = ApprovalProcess.objects.create(
            cycle=self.cycle,
            name="Standard Review",
            is_general=True,
            created_by=self.hr,
        )
        self.hod_step = ApprovalStep.objects.create(
            process=process,
            step_number=2,
            label="HOD Review",
            role_required=ApprovalStep.HOD,
        )
        self.director_step = ApprovalStep.objects.create(
            process=process,
            step_number=3,
            label="Director Review",
            role_required=ApprovalStep.DIRECTORATE,
        )
        self.appraisal = Appraisal.objects.create(
            cycle=self.cycle,
            staff=self.staff,
            supervisor=self.supervisor,
        )
        self.hod_assignment = AppraisalApprovalAssignment.objects.create(
            appraisal=self.appraisal,
            step=self.hod_step,
        )
        self.director_assignment = AppraisalApprovalAssignment.objects.create(
            appraisal=self.appraisal,
            step=self.director_step,
        )
        stale_process = ApprovalProcess.objects.create(
            cycle=self.cycle,
            name="Stale Supervisor Process",
            is_general=False,
            created_by=self.hr,
        )
        self.stale_hod_step = ApprovalStep.objects.create(
            process=stale_process,
            step_number=1,
            label="Stale HOD Review",
            role_required=ApprovalStep.HOD,
        )
        self.stale_hod_assignment = AppraisalApprovalAssignment.objects.create(
            appraisal=self.appraisal,
            step=self.stale_hod_step,
        )
        self.other_department = Department.objects.create(name="Finance", code="BFIN")
        self.other_staff = CustomUser.objects.create_user(
            username="bulk_other_staff",
            password="pass12345",
            staff_id="BULK-OTH-001",
            role=CustomUser.STAFF,
            first_name="Other",
            last_name="Staff",
            department=self.other_department,
        )
        self.other_appraisal = Appraisal.objects.create(
            cycle=self.cycle,
            staff=self.other_staff,
        )
        self.other_hod_assignment = AppraisalApprovalAssignment.objects.create(
            appraisal=self.other_appraisal,
            step=self.hod_step,
        )

    def test_bulk_assign_hod_uses_department_hod(self):
        self.client.login(username="bulk_hr_admin", password="pass12345")

        response = self.client.post(
            reverse("hr_admin:api_bulk_assign", args=[self.cycle.id]),
            data=json.dumps({
                "step_id": self.hod_step.id,
                "logic": "hod",
                "appraisal_ids": [self.appraisal.id],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.hod_assignment.refresh_from_db()
        self.assertEqual(self.hod_assignment.approver, self.hod)
        self.stale_hod_assignment.refresh_from_db()
        self.assertIsNone(self.stale_hod_assignment.approver)

    def test_bulk_assign_hod_ignores_stale_supervisor_logic_for_hod_step(self):
        self.client.login(username="bulk_hr_admin", password="pass12345")

        response = self.client.post(
            reverse("hr_admin:api_bulk_assign", args=[self.cycle.id]),
            data=json.dumps({
                "step_id": self.hod_step.id,
                "logic": "supervisor",
                "appraisal_ids": [self.appraisal.id],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.hod_assignment.refresh_from_db()
        self.assertEqual(self.hod_assignment.approver, self.hod)

    def test_bulk_assign_director_uses_reporting_chain(self):
        self.client.login(username="bulk_hr_admin", password="pass12345")

        response = self.client.post(
            reverse("hr_admin:api_bulk_assign", args=[self.cycle.id]),
            data=json.dumps({
                "step_id": self.director_step.id,
                "logic": "director",
                "appraisal_ids": [self.appraisal.id],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.director_assignment.refresh_from_db()
        self.assertEqual(self.director_assignment.approver, self.director)

    def test_assign_approvers_lists_target_department_hod_even_if_not_branch_member(self):
        self.client.login(username="bulk_hr_admin", password="pass12345")

        response = self.client.get(reverse("hr_admin:assign_approvers", args=[self.cycle.id]))

        self.assertContains(response, "HOD Audit")
        self.assertContains(response, "bulk_staff")
        self.assertNotContains(response, "Other Staff")
        self.assertNotContains(response, "Branch Only")

    def test_bulk_assign_only_updates_targeted_appraisals(self):
        self.client.login(username="bulk_hr_admin", password="pass12345")

        response = self.client.post(
            reverse("hr_admin:api_bulk_assign", args=[self.cycle.id]),
            data=json.dumps({
                "step_id": self.hod_step.id,
                "logic": "hod",
                "appraisal_ids": [self.appraisal.id, self.other_appraisal.id],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.hod_assignment.refresh_from_db()
        self.other_hod_assignment.refresh_from_db()
        self.assertEqual(self.hod_assignment.approver, self.hod)
        self.assertIsNone(self.other_hod_assignment.approver)
