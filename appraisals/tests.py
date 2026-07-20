from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from departments.models import Department
from datetime import timedelta
from .models import (
    Appraisal,
    AppraisalApprovalAssignment,
    AppraisalCycle,
    ApprovalProcess,
    ApprovalStep,
    FormField,
    FormFieldResponse,
    FormSection,
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

    def test_staff_evidence_file_shows_on_reviewer_page(self):
        section = FormSection.objects.create(
            cycle=self.cycle,
            name="Staff Evidence",
            order=1,
        )
        field = FormField.objects.create(
            section=section,
            label="Supporting Document",
            field_type=FormField.NARRATIVE,
            filled_by=FormField.APPRAISEE,
            order=1,
        )
        FormFieldResponse.objects.create(
            appraisal=self.appraisal,
            field=field,
            responded_by=self.staff,
            response_type=FormFieldResponse.PRIMARY,
            text_response="Attached my supporting document.",
            evidence_file="evidence/form_fields/supporting_document.docx",
        )
        self.appraisal.status = Appraisal.SUBMITTED
        self.appraisal.current_step_number = 1
        self.appraisal.save(update_fields=["status", "current_step_number"])
        self.supervisor_assignment.status = AppraisalApprovalAssignment.PENDING
        self.supervisor_assignment.save(update_fields=["status"])

        self.client.login(username="supervisor", password="pass12345")
        response = self.client.get(reverse("appraisals:step_review", args=[self.appraisal.id]))

        self.assertContains(response, "Attached my supporting document.")
        self.assertContains(response, "View attached evidence")
        self.assertContains(response, "/media/evidence/form_fields/supporting_document.docx")

    def test_other_reviewer_general_comment_shows_on_review_page(self):
        self.supervisor_assignment.comments = "Supervisor recommends approval after reviewing the evidence."
        self.supervisor_assignment.save(update_fields=["comments"])

        self.client.login(username="hod", password="pass12345")
        response = self.client.get(reverse("appraisals:step_review", args=[self.appraisal.id]))

        self.assertContains(response, "Reviewer Comments")
        self.assertContains(response, "Supervisor Review")
        self.assertContains(response, "Supervisor recommends approval after reviewing the evidence.")

    def test_result_page_hides_empty_form_sections(self):
        empty_section = FormSection.objects.create(
            cycle=self.cycle,
            name="Section A: To Be Completed by Appraisee",
            description="Complete all fields below before submitting your appraisal.",
            section_weight=0,
            order=1,
        )
        populated_section = FormSection.objects.create(
            cycle=self.cycle,
            name="Section B: Quantitative Appraisal",
            description="Score each KPI.",
            section_weight=100,
            order=2,
        )
        field = FormField.objects.create(
            section=populated_section,
            label="Revenue Target Achieved",
            field_type=FormField.SCORE,
            filled_by=FormField.APPRAISEE,
            max_score=100,
            order=1,
        )
        FormFieldResponse.objects.create(
            appraisal=self.appraisal,
            field=field,
            response_type=FormFieldResponse.PRIMARY,
            score=80,
            responded_by=self.staff,
        )

        self.client.login(username="hod", password="pass12345")
        response = self.client.get(reverse("appraisals:appraisal_result", args=[self.appraisal.id]))

        self.assertNotContains(response, empty_section.name)
        self.assertContains(response, populated_section.name)
        self.assertContains(response, "Revenue Target Achieved")

    def test_authorized_user_can_download_appraisal_result(self):
        self.supervisor_assignment.comments = "Approved with strong KPI evidence."
        self.supervisor_assignment.save(update_fields=["comments"])

        self.client.login(username="hod", password="pass12345")
        response = self.client.get(reverse("appraisals:download_appraisal_result", args=[self.appraisal.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertContains(response, "Appraisal Report")
        self.assertContains(response, "Approved with strong KPI evidence.")

    def test_unauthorized_user_cannot_download_appraisal_result(self):
        outsider = CustomUser.objects.create_user(
            username="outsider",
            password="pass12345",
            staff_id="OUT-001",
            role=CustomUser.STAFF,
        )

        self.client.login(username="outsider", password="pass12345")
        response = self.client.get(reverse("appraisals:download_appraisal_result", args=[self.appraisal.id]))

        self.assertEqual(response.status_code, 302)


class MyAppraisalsStatsTests(TestCase):
    def test_summary_counts_are_scoped_to_logged_in_user(self):
        staff = CustomUser.objects.create_user(
            username="staff_stats",
            password="pass12345",
            staff_id="STF-STATS-001",
            role=CustomUser.STAFF,
        )
        other_staff = CustomUser.objects.create_user(
            username="other_staff_stats",
            password="pass12345",
            staff_id="STF-STATS-002",
            role=CustomUser.STAFF,
        )
        cycle = AppraisalCycle.objects.create(
            name="Stats Review",
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            created_by=staff,
        )
        Appraisal.objects.create(
            cycle=cycle,
            staff=staff,
            status=Appraisal.NOT_STARTED,
        )
        Appraisal.objects.create(
            cycle=cycle,
            staff=other_staff,
            status=Appraisal.SUBMITTED,
        )

        self.client.login(username="staff_stats", password="pass12345")
        response = self.client.get(reverse("appraisals:my_appraisals"))

        self.assertEqual(response.context["total_count"], 1)
        self.assertEqual(response.context["submitted_count"], 0)
        self.assertEqual(response.context["approved_count"], 0)
        self.assertContains(response, ">0</p>", html=False)

    def test_approved_item_links_to_result_page(self):
        staff = CustomUser.objects.create_user(
            username="staff_final_result",
            password="pass12345",
            staff_id="STF-FINAL-001",
            role=CustomUser.STAFF,
        )
        cycle = AppraisalCycle.objects.create(
            name="Final Result Review",
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            created_by=staff,
        )
        appraisal = Appraisal.objects.create(
            cycle=cycle,
            staff=staff,
            status=Appraisal.APPROVED,
            final_score=90,
        )

        self.client.login(username="staff_final_result", password="pass12345")
        response = self.client.get(reverse("appraisals:my_appraisals"))

        self.assertContains(response, "View Result")
        self.assertContains(response, reverse("appraisals:appraisal_result", args=[appraisal.id]))
        self.assertNotContains(response, reverse("appraisals:self_appraisal_form_pk", args=[appraisal.id]))


class ReviewerAppraisalOrderingTests(TestCase):
    def setUp(self):
        self.supervisor = CustomUser.objects.create_user(
            username="reviewer_order",
            password="pass12345",
            staff_id="SUP-ORDER-001",
            role=CustomUser.SUPERVISOR,
            first_name="Sarah",
            last_name="Supervisor",
        )
        self.cycle = AppraisalCycle.objects.create(
            name="Ordering Review",
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            created_by=self.supervisor,
        )
        self.process = ApprovalProcess.objects.create(
            cycle=self.cycle,
            name="Supervisor Review Process",
            is_general=True,
            created_by=self.supervisor,
        )
        self.step = ApprovalStep.objects.create(
            process=self.process,
            step_number=1,
            label="Supervisor Review",
            role_required=ApprovalStep.SUPERVISOR,
        )

        self.old_staff = CustomUser.objects.create_user(
            username="old_submission",
            password="pass12345",
            staff_id="OLD-001",
            role=CustomUser.STAFF,
            first_name="Old",
            last_name="Submission",
            supervisor=self.supervisor,
        )
        self.new_staff = CustomUser.objects.create_user(
            username="new_submission",
            password="pass12345",
            staff_id="NEW-001",
            role=CustomUser.STAFF,
            first_name="New",
            last_name="Submission",
            supervisor=self.supervisor,
        )
        self.not_started_staff = CustomUser.objects.create_user(
            username="not_started_order",
            password="pass12345",
            staff_id="NST-001",
            role=CustomUser.STAFF,
            first_name="Not",
            last_name="Started",
            supervisor=self.supervisor,
        )

        now = timezone.now()
        self.old_appraisal = Appraisal.objects.create(
            cycle=self.cycle,
            staff=self.old_staff,
            status=Appraisal.SUBMITTED,
            current_step_number=1,
            self_submitted_at=now - timedelta(days=2),
        )
        self.new_appraisal = Appraisal.objects.create(
            cycle=self.cycle,
            staff=self.new_staff,
            status=Appraisal.SUBMITTED,
            current_step_number=1,
            self_submitted_at=now,
        )
        self.not_started_appraisal = Appraisal.objects.create(
            cycle=self.cycle,
            staff=self.not_started_staff,
            status=Appraisal.NOT_STARTED,
        )

        for appraisal in [self.old_appraisal, self.new_appraisal]:
            AppraisalApprovalAssignment.objects.create(
                appraisal=appraisal,
                step=self.step,
                approver=self.supervisor,
                status=AppraisalApprovalAssignment.PENDING,
            )

    def test_team_appraisals_show_recent_submissions_first(self):
        self.client.login(username="reviewer_order", password="pass12345")
        response = self.client.get(reverse("appraisals:team_list"))

        ordered_names = [item["member"].username for item in response.context["team_data"]]

        self.assertEqual(ordered_names[0], "new_submission")
        self.assertEqual(ordered_names[1], "old_submission")
        self.assertEqual(ordered_names[-1], "not_started_order")

    def test_review_queue_shows_recent_pending_submission_first(self):
        self.client.login(username="reviewer_order", password="pass12345")
        response = self.client.get(reverse("appraisals:review_queue"))

        ordered_staff = [assignment.appraisal.staff.username for assignment in response.context["current_pending"]]

        self.assertEqual(ordered_staff, ["new_submission", "old_submission"])
