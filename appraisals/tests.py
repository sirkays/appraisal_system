from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from departments.models import Department
from .models import (
    Appraisal,
    AppraisalApprovalAssignment,
    AppraisalCycle,
    ApprovalProcess,
    ApprovalStep,
)


class ReturnReasonVisibilityTests(TestCase):
    def setUp(self):
        self.hod = CustomUser.objects.create_user(
            username="hod",
            password="pass12345",
            staff_id="HOD-001",
            role=CustomUser.HOD,
            first_name="Hannah",
            last_name="HOD",
        )
        self.department = Department.objects.create(
            name="Operations",
            code="OPS",
            hod=self.hod,
        )
        self.hod.department = self.department
        self.hod.save(update_fields=["department"])

        self.supervisor = CustomUser.objects.create_user(
            username="supervisor",
            password="pass12345",
            staff_id="SUP-001",
            role=CustomUser.SUPERVISOR,
            first_name="Sam",
            last_name="Supervisor",
            department=self.department,
        )
        self.staff = CustomUser.objects.create_user(
            username="staff",
            password="pass12345",
            staff_id="STF-001",
            role=CustomUser.STAFF,
            first_name="Stella",
            last_name="Staff",
            department=self.department,
            supervisor=self.supervisor,
        )
        self.cycle = AppraisalCycle.objects.create(
            name="2026 Review",
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            created_by=self.hod,
        )
        self.process = ApprovalProcess.objects.create(
            cycle=self.cycle,
            name="Standard Review",
            is_general=True,
            created_by=self.hod,
        )
        self.supervisor_step = ApprovalStep.objects.create(
            process=self.process,
            step_number=1,
            label="Supervisor Review",
            role_required=ApprovalStep.SUPERVISOR,
        )
        self.hod_step = ApprovalStep.objects.create(
            process=self.process,
            step_number=2,
            label="HOD Review",
            role_required=ApprovalStep.HOD,
        )
        self.appraisal = Appraisal.objects.create(
            cycle=self.cycle,
            staff=self.staff,
            supervisor=self.supervisor,
            status=Appraisal.AWAITING_STEP_REVIEW,
            current_step_number=2,
        )
        self.supervisor_assignment = AppraisalApprovalAssignment.objects.create(
            appraisal=self.appraisal,
            step=self.supervisor_step,
            approver=self.supervisor,
            status=AppraisalApprovalAssignment.APPROVED,
        )
        self.hod_assignment = AppraisalApprovalAssignment.objects.create(
            appraisal=self.appraisal,
            step=self.hod_step,
            approver=self.hod,
            status=AppraisalApprovalAssignment.PENDING,
        )

    def test_higher_step_return_reason_shows_to_previous_reviewer(self):
        self.client.login(username="hod", password="pass12345")

        response = self.client.post(
            reverse("appraisals:step_review", args=[self.appraisal.id]),
            {
                "action": "return",
                "comments": "Please clarify the KPI evidence before approval.",
                "return_comment": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.appraisal.refresh_from_db()
        self.hod_assignment.refresh_from_db()
        self.supervisor_assignment.refresh_from_db()

        self.assertEqual(self.appraisal.status, Appraisal.RETURNED_TO_REVIEWER)
        self.assertEqual(self.appraisal.current_step_number, 1)
        self.assertEqual(
            self.appraisal.hod_return_notes,
            "Please clarify the KPI evidence before approval.",
        )
        self.assertEqual(self.hod_assignment.status, AppraisalApprovalAssignment.RETURNED)
        self.assertEqual(
            self.hod_assignment.comments,
            "Please clarify the KPI evidence before approval.",
        )
        self.assertEqual(self.supervisor_assignment.status, AppraisalApprovalAssignment.PENDING)

        self.client.logout()
        self.client.login(username="supervisor", password="pass12345")
        response = self.client.get(reverse("appraisals:step_review", args=[self.appraisal.id]))

        self.assertContains(response, "Return Reason")
        self.assertContains(response, "HOD Review")
        self.assertContains(response, "Please clarify the KPI evidence before approval.")

    def test_step_one_return_reason_shows_on_review_page(self):
        self.appraisal.status = Appraisal.RETURNED_TO_STAFF
        self.appraisal.current_step_number = 0
        self.appraisal.supervisor_return_notes = "Staff should add measurable achievements."
        self.appraisal.save(update_fields=["status", "current_step_number", "supervisor_return_notes"])
        self.supervisor_assignment.status = AppraisalApprovalAssignment.RETURNED
        self.supervisor_assignment.comments = "Staff should add measurable achievements."
        self.supervisor_assignment.save(update_fields=["status", "comments"])

        self.client.login(username="supervisor", password="pass12345")
        response = self.client.get(reverse("appraisals:step_review", args=[self.appraisal.id]))

        self.assertContains(response, "Return Reason")
        self.assertContains(response, "Supervisor Review")
        self.assertContains(response, "Staff should add measurable achievements.")

    def test_staff_resubmit_requeues_step_one_for_supervisor(self):
        self.appraisal.status = Appraisal.RETURNED_TO_STAFF
        self.appraisal.current_step_number = 0
        self.appraisal.supervisor_return_notes = "Please upload the missing document."
        self.appraisal.save(update_fields=["status", "current_step_number", "supervisor_return_notes"])
        self.supervisor_assignment.status = AppraisalApprovalAssignment.RETURNED
        self.supervisor_assignment.comments = "Please upload the missing document."
        self.supervisor_assignment.save(update_fields=["status", "comments"])

        self.client.login(username="staff", password="pass12345")
        response = self.client.post(
            reverse("appraisals:self_appraisal_form_pk", args=[self.appraisal.id]),
            {"action": "submit"},
        )

        self.assertEqual(response.status_code, 302)
        self.appraisal.refresh_from_db()
        self.supervisor_assignment.refresh_from_db()
        self.assertEqual(self.appraisal.status, Appraisal.SUBMITTED)
        self.assertEqual(self.appraisal.current_step_number, 1)
        self.assertEqual(self.supervisor_assignment.status, AppraisalApprovalAssignment.PENDING)
        self.assertIsNone(self.supervisor_assignment.actioned_at)

        self.client.logout()
        self.client.login(username="supervisor", password="pass12345")
        response = self.client.get(reverse("appraisals:step_review", args=[self.appraisal.id]))
        self.assertNotContains(response, "This appraisal is not currently in your action queue.")

    def test_reapproval_requeues_returning_higher_step_reviewer(self):
        self.appraisal.status = Appraisal.RETURNED_TO_REVIEWER
        self.appraisal.current_step_number = 1
        self.appraisal.save(update_fields=["status", "current_step_number"])
        self.supervisor_assignment.status = AppraisalApprovalAssignment.PENDING
        self.supervisor_assignment.save(update_fields=["status"])
        self.hod_assignment.status = AppraisalApprovalAssignment.RETURNED
        self.hod_assignment.comments = "Please clarify the KPI evidence before approval."
        self.hod_assignment.save(update_fields=["status", "comments"])

        self.client.login(username="supervisor", password="pass12345")
        response = self.client.post(
            reverse("appraisals:step_review", args=[self.appraisal.id]),
            {"action": "approve"},
        )

        self.assertEqual(response.status_code, 302)
        self.appraisal.refresh_from_db()
        self.hod_assignment.refresh_from_db()
        self.assertEqual(self.appraisal.status, Appraisal.AWAITING_STEP_REVIEW)
        self.assertEqual(self.appraisal.current_step_number, 2)
        self.assertEqual(self.hod_assignment.status, AppraisalApprovalAssignment.PENDING)
        self.assertIsNone(self.hod_assignment.actioned_at)

        self.client.logout()
        self.client.login(username="hod", password="pass12345")
        response = self.client.get(reverse("appraisals:step_review", args=[self.appraisal.id]))
        self.assertNotContains(response, "This appraisal is not currently in your action queue.")
