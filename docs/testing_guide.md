# SIRS Appraisal System — Testing Guide

This guide will walk you through testing the completed features of the Staff Performance Appraisal System. By following these steps, you will verify the full lifecycle of an appraisal from the Staff's self-assessment through to the Supervisor's review.

## Prerequisites

Ensure the Django development server is running and the database is populated with the initial test data.

1. **Start the Server**:
   ```bash
   .venv\Scripts\python manage.py runserver 9092
   ```

2. **Seed the Database** (if you haven't already):
   Open a new terminal in the project directory and run:
   ```bash
   .venv\Scripts\python manage.py seed_data
   ```
   *This command creates the departments, the test users, and the active appraisal cycle with predefined KPIs and Competencies.*

---

## Test Accounts

The `seed_data` command provides the following accounts for testing. All accounts (except admin) use the password `pass123`.

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **HR / Admin** | `admin` | `adminpassword123` | System Administrator |
| **HOD** | `hod_tax` | `pass123` | Head of Taxation Department |
| **Supervisor** | `sup_tax` | `pass123` | Direct Manager of Staff |
| **Staff** | `staff_tax` | `pass123` | Subordinate who will be appraised |

---

## Step-by-Step Testing Flow

### Step 1: Staff Self-Appraisal

1. **Log In as Staff**:
   - Navigate to [http://127.0.0.1:9092](http://127.0.0.1:9092).
   - Log in using `staff_tax` and `pass123`.
   - You should be redirected to the **Staff Dashboard**. Notice the Welcome banner and the "Pending" status card.

2. **Fill Out the Appraisal Form**:
   - Click **Start Self-Appraisal** on the dashboard, or use the sidebar link.
   - You will see the form with KPI categories and Competency categories.
   - Enter your *Targets*, *Achievements*, and a *Self Score* (1-5) for the KPIs.
   - Enter your *Self Score* and *Comments* for the Competencies.
   - Scroll down to fill out the narrative sections (Key Achievements, Challenges, etc.).

3. **Save Draft vs Submit**:
   - Try clicking **Save as Draft**. You should be redirected to the dashboard with a success message, and your inputs will be saved.
   - Go back to the form and click **Submit for Review**.
   - Your appraisal status will change to **Submitted**. The form will now be locked (read-only), and your "My Appraisals" page will reflect this status.

### Step 2: Supervisor Review

1. **Log In as Supervisor**:
   - Log out of the staff account.
   - Log back in using `sup_tax` and `pass123`.
   - You will be redirected to the **Supervisor Dashboard**.

2. **Check the Dashboard & Notifications**:
   - Notice the bell icon at the top right has a red dot. Click it to see the notification that `staff_tax` has submitted their appraisal.
   - Your "To Review" counter should show `1`, and the pending submission will appear in the table at the bottom of the dashboard.

3. **Review the Team List**:
   - Click **Team Appraisals** in the left sidebar.
   - You will see John Nwachukwu (`staff_tax`) listed here with a "Submitted" badge and their calculated self-score.
   - Click the **Review** button.

4. **Grade the Appraisal**:
   - On the Review page, you'll see the staff member's scores on the left side, and a panel for you to input the supervisor scores on the right side.
   - Click the score numbers (1-5) to grade each KPI and Competency. Add optional comments.
   - Scroll to the bottom to view the staff's free-text answers.
   - Fill out the **Final Recommendation** dropdown, add any strengths/weaknesses, and overall comments.

5. **Save Draft vs Submit**:
   - Try clicking **Save Draft**. The review will be saved but not submitted. The staff's status on the Team List will show "Submitted (Draft Saved)" and the action button will say "Continue Review".
   - *(Optional Test)* Click **Return to Staff for Revision**. This will push the appraisal back to `staff_tax`, changing the status to "Returned". If you do this, log back in as `staff_tax` to see the notification, edit the form, and re-submit it.
   - Click **Submit to HOD**.
   - The system will calculate the final supervisor score (60% KPI / 40% Competency) and lock the review. The appraisal is now awaiting HOD approval.

### Step 3: HOD Final Approval

1. **Log In as HOD**:
   - Log out of the supervisor account.
   - Log in using `hod_tax` and `pass123`.
   - You will land on the **HOD Dashboard**, displaying department metrics and pending approvals.

2. **Check Department List & Queue**:
   - Notice your "Pending Approval" counter is `1`, and the appraisal from `staff_tax` is in your queue.
   - Click **Department Appraisals** in the sidebar. This lists all staff under your department. The staff member's appraisal status is now `Under Review`.
   - Click **Review** next to the submitted appraisal.

3. **Finalize the Appraisal**:
   - Review the Staff's inputs alongside the Supervisor's scores and recommendations.
   - At the bottom of the page, add optional HOD comments.
   - *(Optional Test)* Click **Return to Supervisor for Revision** if you want to push it back to `sup_tax`.
   - Click **Approve Appraisal**.
   - The status changes to **Approved**, the final score is locked, and notifications are sent out.

### Step 4: Verify the Complete Lifecycle

- **As Staff**: Log in as `staff_tax`. The dashboard shows the appraisal is **Approved**. You have a notification of approval, and clicking "Self Appraisal" shows the completely locked form with all final scores.
- **As Supervisor**: Log in as `sup_tax`. The "Team Appraisals" page shows the staff's appraisal as **Approved**.

---

## What's Next?
If all steps work correctly, the system successfully passes data through the entire chain (Staff -> Supervisor -> HOD). The next major development phase will be building the **HR Administration Portal** to manage the cycles, track system-wide reports, and oversee the entire organization's appraisals!
