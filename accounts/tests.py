from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from appraisals.models import Appraisal, AppraisalCycle


class StaffDashboardResultLinkTests(TestCase):
    def test_finalized_appraisal_links_to_result_page(self):
        staff = CustomUser.objects.create_user(
            username="staff_result",
            password="pass12345",
            staff_id="STF-RESULT-001",
            role=CustomUser.STAFF,
            first_name="New",
            last_name="Staff",
        )
        cycle = AppraisalCycle.objects.create(
            name="Annual Performance Appraisal",
            start_date="2026-01-01",
            end_date="2026-12-31",
            status=AppraisalCycle.ACTIVE,
            created_by=staff,
        )
        appraisal = Appraisal.objects.create(
            cycle=cycle,
            staff=staff,
            status=Appraisal.APPROVED,
            final_score=85,
        )

        self.client.login(username="staff_result", password="pass12345")
        response = self.client.get(reverse("accounts:staff_dashboard"))

        self.assertContains(response, "View Final Result")
        self.assertContains(response, reverse("appraisals:appraisal_result", args=[appraisal.id]))
        self.assertNotContains(response, reverse("appraisals:self_appraisal_form_pk", args=[appraisal.id]))
