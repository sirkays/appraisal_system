from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from decimal import Decimal
from accounts.models import CustomUser
from .models import (
    AppraisalCycle, Appraisal, KPICategory, KPIItem,
    KPIScore, CompetencyCategory, CompetencyItem, CompetencyScore,
    NarrativeField, NarrativeResponse
)

@login_required
def self_appraisal_form(request, pk=None):
    """
    Handles staff self-appraisal form loading, draft saving, and final submission.
    """
    if pk:
        # Load specific appraisal
        from django.shortcuts import get_object_or_404
        appraisal = get_object_or_404(Appraisal, pk=pk, staff=request.user)
        active_cycle = appraisal.cycle
    else:
        # 2. Get active appraisal cycle (legacy fallback)
        active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()
        if not active_cycle:
            messages.warning(request, "There is currently no active appraisal cycle.")
            return redirect('accounts:dashboard_redirect')

        # 3. Fetch or initialize Appraisal
        appraisal, created = Appraisal.objects.get_or_create(
            cycle=active_cycle,
            staff=request.user,
            defaults={
                'status': Appraisal.DRAFT,
                'supervisor': request.user.supervisor,
            }
        )

    # 4. Check if appraisal is already submitted/reviewed/approved (Read-only)
    is_editable = appraisal.status in [Appraisal.NOT_STARTED, Appraisal.DRAFT, Appraisal.RETURNED_TO_STAFF]

    # If it was in NOT_STARTED, change status to DRAFT now that they are editing it
    if appraisal.status == Appraisal.NOT_STARTED:
        appraisal.status = Appraisal.DRAFT
        appraisal.save()

    # 5. Initialize NarrativeResponse for each NarrativeField in cycle
    narrative_fields = active_cycle.narrative_fields.filter(is_supervisor_field=False)
    for field in narrative_fields:
        NarrativeResponse.objects.get_or_create(appraisal=appraisal, field=field)

    # 6. Pre-create empty KPI scores for any KPIs in this cycle
    kpi_items = KPIItem.objects.filter(category__cycle=active_cycle)
    for item in kpi_items:
        KPIScore.objects.get_or_create(appraisal=appraisal, kpi_item=item)

    # 7. Pre-create empty Competency scores for any Competencies in this cycle
    competency_items = CompetencyItem.objects.filter(category__cycle=active_cycle)
    for item in competency_items:
        CompetencyScore.objects.get_or_create(appraisal=appraisal, competency_item=item)

    # 8. Handle Form Submission (POST)
    if request.method == 'POST':
        if not is_editable:
            messages.error(request, "This appraisal is already submitted and cannot be modified.")
            return redirect('appraisals:self_appraisal_form')

        # Retrieve action type: 'save_draft' or 'submit'
        action = request.POST.get('action', 'save_draft')

        # Update Narrative Responses
        for resp in appraisal.narrative_responses.filter(field__is_supervisor_field=False):
            resp.response_text = request.POST.get(f'narrative_{resp.id}', '').strip()
            evidence = request.FILES.get(f'narrative_evidence_{resp.id}')
            if evidence:
                resp.evidence_file = evidence
            resp.save()

        # Update KPI Scores
        kpi_scores = appraisal.kpi_scores.all()
        for score in kpi_scores:
            score_val = request.POST.get(f'kpi_score_{score.id}')
            comment = request.POST.get(f'kpi_comment_{score.id}', '').strip()
            
            score.staff_comment = comment
            if score_val:
                score.self_score = Decimal(score_val)
            else:
                score.self_score = None
                
            evidence = request.FILES.get(f'kpi_evidence_{score.id}')
            if evidence:
                score.evidence_file = evidence
                
            score.save()

        # Update Competency Scores
        competency_scores = appraisal.competency_scores.all()
        for score in competency_scores:
            score_val = request.POST.get(f'competency_score_{score.id}')
            comment = request.POST.get(f'competency_comment_{score.id}', '').strip()
            
            score.staff_comment = comment
            if score_val:
                score.self_score = Decimal(score_val)
            else:
                score.self_score = None
                
            evidence = request.FILES.get(f'comp_evidence_{score.id}')
            if evidence:
                score.evidence_file = evidence
                
            score.save()

        if action == 'submit':
            # Validation: Verify all scores and narrative fields are filled in
            missing_fields = []
            
            # Check narrative details
            for resp in appraisal.narrative_responses.filter(field__is_supervisor_field=False):
                if not resp.response_text:
                    missing_fields.append(resp.field.name)
            
            # Check KPI scores
            for score in kpi_scores:
                if score.self_score is None:
                    missing_fields.append(f"KPI: {score.kpi_item.name} self-score")

            # Check Competency scores
            for score in competency_scores:
                if score.self_score is None:
                    missing_fields.append(f"Competency: {score.competency_item.name} self-score")

            if missing_fields:
                messages.error(
                    request,
                    f"Cannot submit. The following fields are required: {', '.join(missing_fields)}"
                )
                return redirect('appraisals:self_appraisal_form')

            # Calculate overall self-score
            # --- 1. Weighted KPI score ---
            kpi_categories = active_cycle.kpi_categories.all()
            weighted_kpi_total = Decimal('0.00')
            total_kpi_weight = Decimal('0.00')

            for category in kpi_categories:
                # Find all KPI scores belonging to this category
                cat_scores = kpi_scores.filter(kpi_item__category=category)
                if cat_scores.exists():
                    cat_avg = sum(s.self_score for s in cat_scores) / cat_scores.count()
                    weighted_kpi_total += cat_avg * (category.weight / Decimal('100.00'))
                    total_kpi_weight += category.weight

            # --- 2. Weighted Competency score ---
            comp_categories = active_cycle.competency_categories.all()
            weighted_comp_total = Decimal('0.00')
            total_comp_weight = Decimal('0.00')

            for category in comp_categories:
                cat_scores = competency_scores.filter(competency_item__category=category)
                if cat_scores.exists():
                    cat_avg = sum(s.self_score for s in cat_scores) / cat_scores.count()
                    weighted_comp_total += cat_avg * (category.weight / Decimal('100.00'))
                    total_comp_weight += category.weight

            # Blend overall self score: 60% KPI + 40% Competency
            # Adjust if either section weight does not add up to 100, but they should.
            overall_self_score = (weighted_kpi_total * Decimal('0.60')) + (weighted_comp_total * Decimal('0.40'))
            
            # Round score to 2 decimal places
            appraisal.overall_self_score = overall_self_score.quantize(Decimal('0.01'))
            appraisal.status = Appraisal.SUBMITTED
            appraisal.self_submitted_at = timezone.now()
            appraisal.save()
            
            # Notify the supervisor
            from notifications.models import Notification
            if appraisal.supervisor:
                Notification.objects.create(
                    recipient=appraisal.supervisor,
                    sender=request.user,
                    notification_type=Notification.APPRAISAL_SUBMITTED,
                    title="New Self-Appraisal Submitted",
                    message=f"{request.user.get_full_name()} has submitted their self-appraisal and it is awaiting your review.",
                    related_appraisal=appraisal
                )

            messages.success(request, "Your self-appraisal has been submitted successfully to your supervisor!")
            return redirect('accounts:dashboard_redirect')

        else:  # Save Draft
            messages.success(request, "Self-appraisal draft saved successfully.")
            return redirect('appraisals:self_appraisal_form')

    # For GET requests, load categories and structured scores for display
    # Group scores by category for cleaner UI rendering
    kpi_categories = active_cycle.kpi_categories.all().prefetch_related('items')
    comp_categories = active_cycle.competency_categories.all().prefetch_related('items')

    # Map pre-fetched categories to scores
    kpi_scores_by_cat = []
    for cat in kpi_categories:
        scores = appraisal.kpi_scores.filter(kpi_item__category=cat).select_related('kpi_item')
        kpi_scores_by_cat.append({
            'category': cat,
            'scores': scores
        })

    comp_scores_by_cat = []
    for cat in comp_categories:
        scores = appraisal.competency_scores.filter(competency_item__category=cat).select_related('competency_item')
        comp_scores_by_cat.append({
            'category': cat,
            'scores': scores
        })

    context = {
        'cycle': active_cycle,
        'appraisal': appraisal,
        'is_editable': is_editable,
        'narrative_responses': appraisal.narrative_responses.filter(field__is_supervisor_field=False),
        'kpi_scores_by_cat': kpi_scores_by_cat,
        'comp_scores_by_cat': comp_scores_by_cat,
        'scale_range': range(1, active_cycle.scoring_scale + 1),
    }
    return render(request, 'appraisals/self_appraisal_form.html', context)


@login_required
def my_appraisals(request):
    """
    Displays a list of all appraisals belonging to the currently logged-in user.
    Each staff member can view their history across all past and current cycles.
    """
    appraisals = (
        Appraisal.objects
        .filter(staff=request.user)
        .select_related('cycle', 'supervisor')
        .order_by('-cycle__start_date')
    )

    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()

    context = {
        'appraisals': appraisals,
        'active_cycle': active_cycle,
    }
    return render(request, 'appraisals/my_appraisals.html', context)

@login_required
def team_list(request):
    """
    Displays all direct reports of the supervisor and their appraisal status
    for the active cycle.
    """
    if request.user.role != CustomUser.SUPERVISOR and request.user.role != CustomUser.HOD:
        messages.error(request, "Access denied. Only supervisors can view this page.")
        return redirect('accounts:dashboard_redirect')
        
    team = CustomUser.objects.filter(supervisor=request.user).select_related('department')
    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()
    
    team_data = []
    for member in team:
        appraisal = None
        if active_cycle:
            appraisal = Appraisal.objects.filter(staff=member, cycle=active_cycle).first()
        team_data.append({
            'member': member,
            'appraisal': appraisal
        })
        
    context = {
        'team_data': team_data,
        'active_cycle': active_cycle
    }
    return render(request, 'appraisals/team_list.html', context)

@login_required
def supervisor_review(request, pk):
    """
    Handles the supervisor's review of a staff member's appraisal.
    Allows scoring, commenting, and submitting to HOD or returning to staff.
    """
    if request.user.role not in [CustomUser.SUPERVISOR, CustomUser.HOD, CustomUser.HR_ADMIN]:
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    appraisal = get_object_or_404(Appraisal, pk=pk)
    
    # Check if supervisor has right to edit
    is_editable = False
    if request.user == appraisal.supervisor and appraisal.status in [Appraisal.SUBMITTED, Appraisal.RETURNED_TO_SUPERVISOR]:
        is_editable = True
        
    # Get or create supervisor review object
    from .models import SupervisorReview
    sup_review, _ = SupervisorReview.objects.get_or_create(appraisal=appraisal)
    
    if request.method == 'POST':
        if not is_editable:
            messages.error(request, "This appraisal is not currently editable by you.")
            return redirect('appraisals:team_list')
            
        action = request.POST.get('action')
        
        # Save supervisor narrative fields
        for resp in appraisal.narrative_responses.filter(field__is_supervisor_field=True):
            narrative_text = request.POST.get(f'narrative_{resp.id}')
            if narrative_text is not None:
                resp.response_text = narrative_text.strip()
            evidence = request.FILES.get(f'narrative_evidence_{resp.id}')
            if evidence:
                resp.evidence_file = evidence
            resp.save()
        
        # Save scores and comments
        kpi_scores = appraisal.kpi_scores.all()
        for score in kpi_scores:
            sup_score_val = request.POST.get(f'kpi_sup_score_{score.id}')
            sup_comment = request.POST.get(f'kpi_sup_comment_{score.id}', '').strip()
            
            score.supervisor_comment = sup_comment
            if sup_score_val:
                score.supervisor_score = Decimal(sup_score_val)
            score.save()
            
        comp_scores = appraisal.competency_scores.all()
        for score in comp_scores:
            sup_score_val = request.POST.get(f'comp_sup_score_{score.id}')
            sup_comment = request.POST.get(f'comp_sup_comment_{score.id}', '').strip()
            
            score.supervisor_comment = sup_comment
            if sup_score_val:
                score.supervisor_score = Decimal(sup_score_val)
            score.save()
            
        # Save overall review details
        sup_review.overall_comments = request.POST.get('overall_comments', '').strip()
        sup_review.strengths = request.POST.get('strengths', '').strip()
        sup_review.areas_for_improvement = request.POST.get('areas_for_improvement', '').strip()
        sup_review.recommendation = request.POST.get('recommendation', '')
        sup_review.reviewer = request.user
        sup_review.save()
        
        if action == 'save_draft':
            messages.success(request, "Review draft saved successfully.")
            return redirect('appraisals:supervisor_review', pk=appraisal.id)
            
        elif action == 'return_to_staff':
            appraisal.status = Appraisal.RETURNED_TO_STAFF
            
            return_comment = request.POST.get('return_comment', '').strip()
            if return_comment:
                appraisal.supervisor_return_notes = return_comment
                
            appraisal.save()
            
            return_comment = request.POST.get('return_comment', '').strip()
            msg = "Your supervisor has returned your self-appraisal for revision."
            if return_comment:
                msg += f" Reason: {return_comment}"
                
            # Generate Notification for staff
            from notifications.models import Notification
            Notification.objects.create(
                recipient=appraisal.staff,
                sender=request.user,
                notification_type=Notification.APPRAISAL_RETURNED,
                title="Appraisal Returned for Revision",
                message=msg,
                related_appraisal=appraisal
            )
            messages.success(request, f"Appraisal returned to {appraisal.staff.get_full_name()} for revision.")
            return redirect('accounts:dashboard_redirect')
            
        elif action == 'submit_to_hod':
            # Validate all scores are given
            missing_fields = []
            for score in kpi_scores:
                if score.supervisor_score is None:
                    missing_fields.append(f"KPI: {score.kpi_item.name} supervisor score")
            for score in comp_scores:
                if score.supervisor_score is None:
                    missing_fields.append(f"Competency: {score.competency_item.name} supervisor score")
                    
            for resp in appraisal.narrative_responses.filter(field__is_supervisor_field=True):
                if not resp.response_text:
                    missing_fields.append(f"Narrative: {resp.field.name}")
                    
            if not sup_review.recommendation:
                missing_fields.append("Overall Recommendation")
                
            if missing_fields:
                messages.error(request, f"Cannot submit. The following fields are required: {', '.join(missing_fields)}")
                return redirect('appraisals:supervisor_review', pk=appraisal.id)
                
            # Calculate overall supervisor score
            active_cycle = appraisal.cycle
            
            # Weighted KPI score
            kpi_categories = active_cycle.kpi_categories.all()
            weighted_kpi_total = Decimal('0.00')
            for category in kpi_categories:
                cat_scores = kpi_scores.filter(kpi_item__category=category)
                if cat_scores.exists():
                    cat_avg = sum(s.supervisor_score for s in cat_scores) / cat_scores.count()
                    weighted_kpi_total += cat_avg * (category.weight / Decimal('100.00'))
                    
            # Weighted Competency score
            comp_categories = active_cycle.competency_categories.all()
            weighted_comp_total = Decimal('0.00')
            for category in comp_categories:
                cat_scores = comp_scores.filter(competency_item__category=category)
                if cat_scores.exists():
                    cat_avg = sum(s.supervisor_score for s in cat_scores) / cat_scores.count()
                    weighted_comp_total += cat_avg * (category.weight / Decimal('100.00'))
                    
            overall_sup_score = (weighted_kpi_total * Decimal('0.60')) + (weighted_comp_total * Decimal('0.40'))
            
            appraisal.overall_supervisor_score = overall_sup_score.quantize(Decimal('0.01'))
            appraisal.status = Appraisal.UNDER_REVIEW # Awaiting HOD
            appraisal.supervisor_reviewed_at = timezone.now()
            appraisal.save()
            
            # Notify HOD
            from notifications.models import Notification
            if appraisal.staff.department and appraisal.staff.department.hod:
                Notification.objects.create(
                    recipient=appraisal.staff.department.hod,
                    sender=request.user,
                    notification_type=Notification.APPRAISAL_REVIEWED,
                    title="New Appraisal Awaiting HOD Approval",
                    message=f"Supervisor {request.user.get_full_name()} has reviewed and submitted an appraisal for {appraisal.staff.get_full_name()}.",
                    related_appraisal=appraisal
                )
            
            messages.success(request, f"Review completed and submitted to HOD successfully.")
            return redirect('accounts:dashboard_redirect')
            
    # GET request - prepare context
    kpi_scores_by_cat = []
    kpi_categories = appraisal.cycle.kpi_categories.all()
    for cat in kpi_categories:
        scores = appraisal.kpi_scores.filter(kpi_item__category=cat).select_related('kpi_item')
        kpi_scores_by_cat.append({'category': cat, 'scores': scores})
        
    comp_scores_by_cat = []
    comp_categories = appraisal.cycle.competency_categories.all()
    for cat in comp_categories:
        scores = appraisal.competency_scores.filter(competency_item__category=cat).select_related('competency_item')
        comp_scores_by_cat.append({'category': cat, 'scores': scores})
        
    context = {
        'appraisal': appraisal,
        'sup_review': sup_review,
        'narrative_responses': appraisal.narrative_responses.all(),
        'kpi_scores_by_cat': kpi_scores_by_cat,
        'comp_scores_by_cat': comp_scores_by_cat,
        'is_editable': is_editable,
        'scale_range': range(1, appraisal.cycle.scoring_scale + 1),
        'recommendation_choices': SupervisorReview.RECOMMENDATION_CHOICES
    }
    return render(request, 'appraisals/supervisor_review.html', context)


@login_required
def department_appraisals(request):
    """
    Displays all staff in the HOD's department and their appraisal status.
    """
    if request.user.role != CustomUser.HOD:
        messages.error(request, "Access denied. Only Heads of Department can view this page.")
        return redirect('accounts:dashboard_redirect')
        
    dept_staff = CustomUser.objects.filter(department=request.user.department)
    active_cycle = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).first()
    
    dept_data = []
    for member in dept_staff:
        appraisal = None
        if active_cycle:
            appraisal = Appraisal.objects.filter(staff=member, cycle=active_cycle).first()
        dept_data.append({
            'member': member,
            'appraisal': appraisal
        })
        
    context = {
        'dept_data': dept_data,
        'active_cycle': active_cycle
    }
    return render(request, 'appraisals/department_list.html', context)


@login_required
def hod_review(request, pk):
    """
    HOD review and final approval of an appraisal.
    """
    if request.user.role != CustomUser.HOD:
        messages.error(request, "Access denied.")
        return redirect('accounts:dashboard_redirect')
        
    appraisal = get_object_or_404(Appraisal, pk=pk)
    
    # Ensure HOD is reviewing someone in their department
    if appraisal.staff.department != request.user.department:
        messages.error(request, "Access denied. This staff member is not in your department.")
        return redirect('accounts:dashboard_redirect')
        
    is_editable = appraisal.status == Appraisal.UNDER_REVIEW
    
    from .models import HODReview, SupervisorReview
    hod_review_obj, _ = HODReview.objects.get_or_create(appraisal=appraisal)
    
    if request.method == 'POST':
        if not is_editable:
            messages.error(request, "This appraisal is not currently awaiting HOD approval.")
            return redirect('appraisals:department_appraisals')
            
        action = request.POST.get('action')
        comments = request.POST.get('comments', '').strip()
        
        hod_review_obj.comments = comments
        hod_review_obj.reviewer = request.user
        
        from notifications.models import Notification
        from django.utils import timezone
        
        if action == 'approve':
            hod_review_obj.action = HODReview.APPROVED
            hod_review_obj.save()
            
            appraisal.status = Appraisal.APPROVED
            appraisal.final_score = appraisal.overall_supervisor_score
            appraisal.hod_reviewed_at = timezone.now()
            appraisal.save()
            
            # Notify staff and supervisor
            Notification.objects.create(
                recipient=appraisal.staff,
                sender=request.user,
                notification_type=Notification.APPRAISAL_APPROVED,
                title="Appraisal Approved",
                message=f"Your appraisal for {appraisal.cycle.name} has been approved by the HOD.",
                related_appraisal=appraisal
            )
            if appraisal.supervisor:
                Notification.objects.create(
                    recipient=appraisal.supervisor,
                    sender=request.user,
                    notification_type=Notification.APPRAISAL_APPROVED,
                    title="Team Appraisal Approved",
                    message=f"The appraisal for {appraisal.staff.get_full_name()} has been approved.",
                    related_appraisal=appraisal
                )
                
            messages.success(request, f"Appraisal for {appraisal.staff.get_full_name()} has been approved.")
            
        elif action == 'return_to_supervisor':
            hod_review_obj.action = HODReview.RETURNED
            hod_review_obj.save()
            
            appraisal.status = Appraisal.RETURNED_TO_SUPERVISOR
            
            return_comment = request.POST.get('return_comment', '').strip()
            if return_comment:
                appraisal.hod_return_notes = return_comment
                
            appraisal.save()
            
            return_comment = request.POST.get('return_comment', '').strip()
            msg = f"The appraisal for {appraisal.staff.get_full_name()} was returned for revision by the HOD."
            if return_comment:
                msg += f" Reason: {return_comment}"
            
            # Notify supervisor
            if appraisal.supervisor:
                Notification.objects.create(
                    recipient=appraisal.supervisor,
                    sender=request.user,
                    notification_type=Notification.APPRAISAL_RETURNED,
                    title="Appraisal Returned by HOD",
                    message=msg,
                    related_appraisal=appraisal
                )
            
            messages.success(request, f"Appraisal returned to supervisor for revision.")
            
        return redirect('appraisals:department_appraisals')
        
    # GET request - prepare context
    kpi_scores_by_cat = []
    for cat in appraisal.cycle.kpi_categories.all():
        scores = appraisal.kpi_scores.filter(kpi_item__category=cat).select_related('kpi_item')
        kpi_scores_by_cat.append({'category': cat, 'scores': scores})
        
    comp_scores_by_cat = []
    for cat in appraisal.cycle.competency_categories.all():
        scores = appraisal.competency_scores.filter(competency_item__category=cat).select_related('competency_item')
        comp_scores_by_cat.append({'category': cat, 'scores': scores})
        
    context = {
        'appraisal': appraisal,
        'sup_review': getattr(appraisal, 'supervisor_review', None),
        'narrative_responses': appraisal.narrative_responses.all(),
        'hod_review': hod_review_obj,
        'kpi_scores_by_cat': kpi_scores_by_cat,
        'comp_scores_by_cat': comp_scores_by_cat,
        'is_editable': is_editable,
    }
    return render(request, 'appraisals/hod_review.html', context)
