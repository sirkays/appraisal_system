# SIRS Staff Performance Appraisal System — Comprehensive Testing Guide

This guide provides a complete walkthrough for testing the full lifecycle of the Staff Performance Appraisal System. It covers all user roles, from the HR Administrator managing the cycles to the Staff performing self-assessments, and the management (Supervisors and HODs) reviewing them.

---

## Accessing the System

**Live Environment:** [https://appraisalsystem.site](https://appraisalsystem.site)  
*(If testing locally, start your server with `python manage.py runserver` and navigate to `http://127.0.0.1:8000`)*

### Default Test Accounts
If the database has been seeded with test data, use the following accounts (otherwise, HR Admin can create them):

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **HR / Admin** | `admin` | `adminpassword123` | Full system administration and cycle management. |
| **HOD** | `hod_tax` | `pass123` | Head of Taxation Department (Final Approval). |
| **Supervisor** | `sup_tax` | `pass123` | Direct Manager (First Reviewer). |
| **Staff** | `staff_tax` | `pass123` | Subordinate (Appraisee). |

---

## Phase 1: HR Administration (Setup)

**Role:** HR / Admin (`admin`)

1. **Log In to the HR Portal**:
   - Log in using the `admin` credentials.
   - You will be directed to the **HR Dashboard**, which displays an overview of active cycles, staff counts, and recent activities.

2. **Manage Departments & Staff**:
   - Navigate to **Departments** in the sidebar. Verify you can add or edit departments.
   - Navigate to **Staff Directory**. Verify you can view staff details, assign them to departments, and assign their supervisors/HODs.

3. **Manage Appraisal Cycles**:
   - Navigate to **Appraisal Cycles**.
   - Create a new cycle (e.g., "2025 Annual Review") or edit an existing one.
   - **Settings:** Inside a cycle, configure the **KPIs**, **Competencies**, and **Narrative Questions**.
   - Set the cycle status to **Active** to allow staff to begin their appraisals.

4. **Verify System Setup**:
   - Ensure that the cycle is visible on the HR Dashboard as the "Active Cycle".

---

## Phase 2: The Appraisal Workflow

### Step 1: Staff Self-Appraisal
**Role:** Staff (`staff_tax`)

1. **Log In & Dashboard**:
   - Log in as `staff_tax`. The dashboard will show a "Pending" appraisal for the active cycle.
2. **Complete the Form**:
   - Click **Start Self-Appraisal**.
   - Fill in your *Targets*, *Achievements*, and *Self Score* (1-5) for the quantitative KPIs.
   - Grade yourself on the qualitative Competencies and add comments.
   - Fill out the required narrative sections (Challenges, Key Achievements, etc.).
3. **Save and Submit**:
   - Test **Save as Draft** to ensure your data is saved without submitting.
   - Click **Submit for Review**. The status will change to **Submitted**, and the form will be locked for editing.

### Step 2: Supervisor Review
**Role:** Supervisor (`sup_tax`)

1. **Dashboard & Notifications**:
   - Log in as `sup_tax`. Check the notification bell for a new submission alert.
   - Your "To Review" dashboard counter should indicate a pending appraisal.
2. **Grade the Appraisal**:
   - Navigate to **Team Appraisals** and click **Review** next to the staff member's name.
   - Review the staff's self-scores. 
   - Input the **Supervisor Scores** (1-5) for each KPI and Competency.
   - Add supervisor comments and fill out the Final Recommendation section.
3. **Actions**:
   - *(Optional)* Use **Return to Staff for Revision** to send it back. (If tested, staff must re-submit).
   - Click **Submit to HOD**. The system calculates the weighted final score and forwards it to the HOD.

### Step 3: HOD Final Approval
**Role:** HOD (`hod_tax`)

1. **Review & Approve**:
   - Log in as `hod_tax`. Check the notification bell.
   - Navigate to **Department Appraisals**. You will see the appraisal marked as `Under Review`.
   - Click **Review** to see both the Staff's inputs and the Supervisor's grades/comments.
   - Add an HOD Comment at the bottom.
   - Click **Approve Appraisal**. The status updates to **Approved** and the final score is permanently locked.

---

## Phase 3: Reporting & Edge Cases

1. **Verifying Completion (Staff)**:
   - Log back in as `staff_tax`. Verify the dashboard shows the appraisal as **Approved** and you can view the finalized, read-only document.

2. **HR Admin Reports & Overrides**:
   - Log in as `admin`. 
   - Navigate to **Reports** to view system-wide analytics (e.g., Average scores, Completion rates).
   - In the **Appraisal Cycles** view, HR can manually **Remove Appraisals** if a restart is needed, or **Re-add Staff** who were mistakenly excluded.

3. **Data Export (If configured)**:
   - HR Admins can test generating Excel or Word dumps from the Reports section to verify data export functionality for payroll/promotions.

---

**End of Testing Guide**  
*Please report any bugs, miscalculations in scoring, or workflow dead-ends to the development team.*
