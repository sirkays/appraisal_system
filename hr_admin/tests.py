from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from appraisals.models import Appraisal, AppraisalCycle
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
