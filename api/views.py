from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model

from accounts.models import CustomUser
from appraisals.models import (
    AppraisalCycle, Appraisal, ApprovalProcess, ApprovalStep,
    AppraisalApprovalAssignment, FormSection, FormField, FormFieldResponse,
    AppraisalReturnLog
)
from departments.models import Department
from branches.models import Branch
from notifications.models import Notification
from .permissions import IsNotHRAdmin, IsHRAdmin
from .serializers import (
    UserSerializer, AppraisalCycleSerializer, AppraisalListSerializer,
    AppraisalDetailSerializer, FormSectionSerializer, FormFieldResponseSerializer,
    NotificationSerializer, ApprovalAssignmentSerializer, DepartmentSerializer,
    BranchSerializer
)

User = get_user_model()


class AuthLoginView(APIView):
    """
    POST /api/auth/login/
    Obtains DRF Token for username/password.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'error': 'Account is inactive.'}, status=status.HTTP_403_FORBIDDEN)

        token, _ = Token.objects.get_or_create(user=user)
        user_data = UserSerializer(user).data

        return Response({
            'token': token.key,
            'user': user_data
        })


class AuthLogoutView(APIView):
    """
    POST /api/auth/logout/
    Deletes the active user's DRF auth token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        return Response({'message': 'Successfully logged out.'})


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Allows authenticated users to change their password via REST API.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password', '')
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')

        if not request.user.check_password(current_password):
            return Response({'error': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'New password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'error': 'New password and confirmation do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save()

        token, _ = Token.objects.get_or_create(user=request.user)

        return Response({
            'message': 'Password changed successfully.',
            'token': token.key
        })


class UserProfileView(APIView):
    """
    GET /api/me/
    Returns current authenticated user details.
    PATCH /api/me/
    Updates current user's profile info (first_name, last_name, email, phone, designation).
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        data = request.data
        if 'first_name' in data:
            user.first_name = str(data['first_name']).strip()
        if 'last_name' in data:
            user.last_name = str(data['last_name']).strip()
        if 'email' in data:
            user.email = str(data['email']).strip()
        if 'phone' in data:
            user.phone = str(data['phone']).strip()
        if 'designation' in data:
            user.designation = str(data['designation']).strip()

        user.save()
        serializer = UserSerializer(user, context={'request': request})
        return Response({
            'message': 'Profile updated successfully.',
            'user': serializer.data
        })


class UserProfileAvatarView(APIView):
    """
    POST /api/me/avatar/
    Uploads or updates the authenticated user's profile picture.
    Stores via Cloudinary when CLOUDINARY credentials are set in .env.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        file_obj = request.FILES.get('profile_picture')
        if not file_obj:
            return Response({'error': 'No profile picture file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        user.profile_picture = file_obj
        user.save()

        serializer = UserSerializer(user, context={'request': request})
        return Response({
            'message': 'Profile picture updated successfully.',
            'user': serializer.data
        })


def _get_eligible_cycles_for_user(user):
    """
    Return a list of active AppraisalCycle objects the given user is eligible
    to participate in.  HR admins see all active cycles.
    """
    qs = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE).order_by('-start_date')
    if user.role == CustomUser.HR_ADMIN or user.is_staff:
        return list(qs)
    return [c for c in qs if user in c.get_eligible_staff()]


class CyclesListView(APIView):
    """
    GET /api/cycles/
    Returns all active appraisal cycles the authenticated user is eligible for.
    This powers the cycle switcher in the mobile app.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def get(self, request):
        eligible = _get_eligible_cycles_for_user(request.user)
        serializer = AppraisalCycleSerializer(eligible, many=True)
        return Response(serializer.data)


class SwitchCycleView(APIView):
    """
    POST /api/cycles/switch/
    Body: { "cycle_id": <int> }
    Sets the user's active cycle preference (stored in the session via a
    dedicated flag on the response so the mobile app can persist it locally).
    Returns the selected cycle data or 403 if the user is not eligible.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def post(self, request):
        cycle_id = request.data.get('cycle_id')
        if not cycle_id:
            return Response({'error': 'cycle_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cycle = AppraisalCycle.objects.get(pk=int(cycle_id), status=AppraisalCycle.ACTIVE)
        except (ValueError, AppraisalCycle.DoesNotExist):
            return Response({'error': 'Cycle not found or not active.'}, status=status.HTTP_404_NOT_FOUND)

        eligible = _get_eligible_cycles_for_user(request.user)
        if cycle not in eligible:
            return Response(
                {'error': 'You are not eligible to participate in this cycle.'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            'message': 'Active cycle updated.',
            'cycle': AppraisalCycleSerializer(cycle).data
        })


class DashboardView(APIView):
    """
    GET /api/dashboard/?cycle_id=<int>  (cycle_id optional)
    Returns role-tailored dashboard metrics for the user's eligible active cycle.

    If cycle_id is provided and the user is eligible, that cycle is used.
    Otherwise the most recent eligible cycle is returned.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def get(self, request):
        user = request.user

        eligible = _get_eligible_cycles_for_user(user)
        active_cycle = None
        cycle_id_param = request.query_params.get('cycle_id')
        if cycle_id_param:
            try:
                requested = next((c for c in eligible if c.id == int(cycle_id_param)), None)
                active_cycle = requested
            except (ValueError, TypeError):
                pass
        if not active_cycle:
            active_cycle = eligible[0] if eligible else None

        cycle_data = AppraisalCycleSerializer(active_cycle).data if active_cycle else None

        # Staff metrics
        my_active_appraisal = None
        if active_cycle:
            my_appraisal = Appraisal.objects.filter(cycle=active_cycle, staff=user).first()
            if my_appraisal:
                my_active_appraisal = AppraisalListSerializer(my_appraisal).data

        my_completed_count = Appraisal.objects.filter(
            staff=user,
            status__in=[Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED]
        ).count()

        # Reviewer metrics
        pending_reviews_count = AppraisalApprovalAssignment.objects.filter(
            approver=user,
            status=AppraisalApprovalAssignment.PENDING,
            appraisal__status__in=[Appraisal.SUBMITTED, Appraisal.AWAITING_STEP_REVIEW, Appraisal.RETURNED_TO_REVIEWER]
        ).count()

        unread_notifications_count = Notification.objects.filter(recipient=user, is_read=False).count()

        return Response({
            'user': UserSerializer(user).data,
            'active_cycle': cycle_data,
            'my_active_appraisal': my_active_appraisal,
            'my_completed_count': my_completed_count,
            'pending_reviews_count': pending_reviews_count,
            'unread_notifications_count': unread_notifications_count,
        })


class MyAppraisalsListView(APIView):
    """
    GET /api/appraisals/my/
    Returns all appraisals for the current staff member.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def get(self, request):
        appraisals = Appraisal.objects.filter(staff=request.user).select_related('cycle', 'staff')
        serializer = AppraisalListSerializer(appraisals, many=True)
        return Response(serializer.data)


class StartAppraisalView(APIView):
    """
    POST /api/appraisals/start/
    Body: { "cycle_id": <int> }  (optional — defaults to most recent eligible cycle)

    Mirrors the web self_appraisal_form get_or_create logic:
      - Resolves the active cycle the user is eligible for
      - Creates or fetches the Appraisal record for (cycle, staff)
      - Advances status from NOT_STARTED → DRAFT
      - Returns the full AppraisalDetailSerializer so the app can open the form immediately
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def post(self, request):
        eligible = _get_eligible_cycles_for_user(request.user)
        if not eligible:
            return Response(
                {'error': 'There is no active appraisal cycle you are eligible for.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Resolve requested cycle
        cycle_id = request.data.get('cycle_id')
        active_cycle = None
        if cycle_id:
            try:
                active_cycle = next((c for c in eligible if c.id == int(cycle_id)), None)
            except (ValueError, TypeError):
                pass
        if not active_cycle:
            active_cycle = eligible[0]

        # get_or_create the appraisal
        appraisal, created = Appraisal.objects.get_or_create(
            cycle=active_cycle,
            staff=request.user,
            defaults={
                'status': Appraisal.DRAFT,
                'supervisor': request.user.supervisor if hasattr(request.user, 'supervisor') else None,
            }
        )

        # Bump NOT_STARTED → DRAFT so the form is immediately editable
        if appraisal.status == Appraisal.NOT_STARTED:
            appraisal.status = Appraisal.DRAFT
            appraisal.save(update_fields=['status'])

        # Only editable statuses may enter the form
        if appraisal.status not in [Appraisal.DRAFT, Appraisal.RETURNED_TO_STAFF]:
            return Response(
                {
                    'error': 'This appraisal has already been submitted and cannot be restarted.',
                    'appraisal': AppraisalDetailSerializer(appraisal).data,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'message': 'Appraisal ready.' if not created else 'Appraisal created.',
            'appraisal': AppraisalDetailSerializer(appraisal).data,
        }, status=status.HTTP_200_OK)


class AppraisalDetailView(APIView):
    """
    GET /api/appraisals/<id>/
    Returns full details for a given appraisal including dynamic sections and responses.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def get(self, request, pk):
        appraisal = get_object_or_404(Appraisal, pk=pk)
        # Check permissions
        can_view = (
            appraisal.staff == request.user or
            appraisal.approval_assignments.filter(approver=request.user).exists()
        )
        if not can_view:
            return Response({'error': 'Not authorized to view this appraisal.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = AppraisalDetailSerializer(appraisal)
        return Response(serializer.data)


class SelfAppraisalSubmitView(APIView):
    """
    POST /api/appraisals/<id>/self-submit/
    Save draft or submit self-appraisal form responses.
    Request payload:
    {
      "action": "submit" | "draft",
      "responses": [
         {"field_id": 1, "text_response": "...", "score": 8.5, "selected_options": ["..."]}
      ]
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def post(self, request, pk):
        appraisal = get_object_or_404(Appraisal, pk=pk, staff=request.user)

        if appraisal.status not in [Appraisal.NOT_STARTED, Appraisal.DRAFT, Appraisal.RETURNED_TO_STAFF]:
            return Response({'error': 'This appraisal cannot be edited at this time.'}, status=status.HTTP_400_BAD_REQUEST)

        action = request.data.get('action', 'draft')
        responses_data = request.data.get('responses', [])

        with transaction.atomic():
            for item in responses_data:
                field_id = item.get('field_id')
                if not field_id:
                    continue
                field = FormField.objects.filter(id=field_id, section__cycle=appraisal.cycle).first()
                if not field:
                    continue

                resp_obj, _ = FormFieldResponse.objects.get_or_create(
                    appraisal=appraisal,
                    field=field,
                    responded_by=request.user,
                    response_type=FormFieldResponse.PRIMARY,
                )

                if 'text_response' in item:
                    resp_obj.text_response = item['text_response'] or ''
                if 'score' in item and item['score'] is not None:
                    try:
                        resp_obj.score = Decimal(str(item['score']))
                    except Exception:
                        resp_obj.score = None
                if 'selected_options' in item:
                    resp_obj.selected_options = item['selected_options'] or []

                resp_obj.save()

            if action == 'submit':
                appraisal.status = Appraisal.SUBMITTED
                appraisal.self_submitted_at = timezone.now()
                appraisal.current_step_number = 1

                # Calculate overall self score if sections are scored
                self_score = _calculate_self_score(appraisal)
                if self_score is not None:
                    appraisal.overall_self_score = self_score

                appraisal.save()

                # Ensure assignments exist for step 1 and notify approver
                _setup_and_notify_step_1(appraisal, request.user)
            else:
                appraisal.status = Appraisal.DRAFT
                appraisal.save()

        return Response({
            'message': 'Appraisal submitted successfully.' if action == 'submit' else 'Draft saved successfully.',
            'appraisal': AppraisalDetailSerializer(appraisal).data
        })


class ReviewQueueListView(APIView):
    """
    GET /api/review/queue/
    Returns pending appraisal reviews assigned to current user.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def get(self, request):
        user = request.user
        assignments = AppraisalApprovalAssignment.objects.filter(
            approver=user,
            status=AppraisalApprovalAssignment.PENDING,
            appraisal__status__in=[
                Appraisal.SUBMITTED,
                Appraisal.AWAITING_STEP_REVIEW,
                Appraisal.RETURNED_TO_REVIEWER
            ]
        ).select_related('appraisal', 'appraisal__staff', 'appraisal__cycle', 'step')

        queue_data = []
        for ass in assignments:
            # Only include the assignment corresponding to the appraisal's CURRENT active step
            if ass.step and ass.step.step_number != ass.appraisal.current_step_number:
                continue

            appraisal = ass.appraisal

            # Build a map of STEP_N -> role from the GENERAL process
            # so the mobile app can resolve STEP_N form fields correctly
            general_process = appraisal.cycle.approval_processes.filter(is_general=True).first()
            general_step_role_map = {}
            if general_process:
                for gstep in general_process.steps.all():
                    general_step_role_map[f'STEP_{gstep.step_number}'] = gstep.role_required

            # Collect roles present in the active process for smart step resolution
            active_process = appraisal.active_process
            active_process_roles = []
            if active_process:
                active_process_roles = list(
                    active_process.steps.values_list('role_required', flat=True)
                )

            queue_data.append({
                'assignment_id': ass.id,
                'step_number': ass.step.step_number,
                'step_label': ass.step.label,
                'role_required': ass.step.role_required,
                'action_label_approve': ass.step.action_label_approve,
                'action_label_return': ass.step.action_label_return,
                'appraisal': AppraisalListSerializer(appraisal, context={'request': request}).data,
                'general_step_role_map': general_step_role_map,
                'active_step_number': ass.step.step_number,
                'active_process_roles': active_process_roles,
            })

        return Response(queue_data)


class StepReviewSubmitView(APIView):
    """
    POST /api/review/<id>/step/
    Submit step review action (Approve & Forward OR Return for Revision).
    Request payload:
    {
      "action": "APPROVE" | "RETURN",
      "comments": "...",
      "responses": [
         {"field_id": 1, "response_type": "PRIMARY", "text_response": "...", "score": 9.0}
      ]
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def post(self, request, pk):
        appraisal = get_object_or_404(Appraisal, pk=pk)
        assignment = appraisal.approval_assignments.filter(
            approver=request.user,
            status=AppraisalApprovalAssignment.PENDING
        ).first()

        if not assignment:
            return Response({'error': 'You do not have a pending review assignment for this appraisal.'}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get('action', 'APPROVE').upper()
        comments = request.data.get('comments', '')
        responses_data = request.data.get('responses', [])

        with transaction.atomic():
            # Save any reviewer form field responses / scores
            for item in responses_data:
                field_id = item.get('field_id')
                resp_type = item.get('response_type', FormFieldResponse.PRIMARY)
                if not field_id:
                    continue
                field = FormField.objects.filter(id=field_id, section__cycle=appraisal.cycle).first()
                if not field:
                    continue

                resp_obj, _ = FormFieldResponse.objects.get_or_create(
                    appraisal=appraisal,
                    field=field,
                    responded_by=request.user,
                    response_type=resp_type,
                )

                if 'text_response' in item:
                    resp_obj.text_response = item['text_response'] or ''
                if 'score' in item and item['score'] is not None:
                    try:
                        resp_obj.score = Decimal(str(item['score']))
                    except Exception:
                        resp_obj.score = None
                    # Clamp score to field bounds
                    if resp_obj.score is not None:
                        if resp_type == FormFieldResponse.REVIEWER_SCORE:
                            resp_obj.score = max(Decimal('0'), min(field.reviewer_score_max, resp_obj.score))
                        else:
                            resp_obj.score = max(field.min_score, min(field.max_score, resp_obj.score))
                if 'selected_options' in item:
                    resp_obj.selected_options = item['selected_options'] or []

                resp_obj.save()

            assignment.comments = comments

            if action in ('SAVE_DRAFT', 'SAVE', 'DRAFT'):
                assignment.save()
                return Response({
                    'message': 'Review draft saved successfully.',
                    'appraisal': AppraisalDetailSerializer(appraisal, context={'request': request}).data
                })

            assignment.actioned_at = timezone.now()

            if action == 'APPROVE':
                assignment.status = AppraisalApprovalAssignment.APPROVED
                assignment.save()

                # Calculate overall supervisor score if available
                sup_score = _calculate_supervisor_score(appraisal)
                if sup_score is not None:
                    appraisal.overall_supervisor_score = sup_score

                # Advance to next step or set APPROVED
                _advance_workflow(appraisal, assignment, request.user)
            elif action == 'RETURN':
                assignment.status = AppraisalApprovalAssignment.RETURNED
                assignment.comments = comments
                assignment.save()

                current_step_number = appraisal.current_step_number
                to_step_number = 0

                if current_step_number <= 1:
                    # Step 1 — return straight to the appraisee
                    appraisal.status = Appraisal.RETURNED_TO_STAFF
                    appraisal.supervisor_return_notes = comments
                    appraisal.current_step_number = 0
                    appraisal.save()

                    # Notify staff
                    try:
                        Notification.objects.create(
                            recipient=appraisal.staff,
                            sender=request.user,
                            notification_type=Notification.APPRAISAL_RETURNED,
                            title="Your Appraisal Has Been Returned for Revision",
                            message=(
                                f"Your appraisal for {appraisal.cycle.name} was returned by "
                                f"{request.user.full_name}: {comments}"
                                if comments else
                                f"Your appraisal for {appraisal.cycle.name} has been returned for revision."
                            ),
                            related_appraisal=appraisal,
                        )
                    except Exception:
                        pass

                else:
                    # Higher steps — return to the previous reviewer
                    prev_step_number = current_step_number - 1
                    to_step_number = prev_step_number
                    process = appraisal.active_process
                    prev_step = (
                        process.steps.filter(step_number=prev_step_number).first()
                        if process else None
                    )

                    appraisal.status = Appraisal.RETURNED_TO_REVIEWER
                    appraisal.hod_return_notes = comments
                    appraisal.current_step_number = prev_step_number
                    appraisal.save()

                    if prev_step:
                        prev_assignment = appraisal.approval_assignments.filter(
                            step=prev_step
                        ).first()
                        if prev_assignment:
                            prev_assignment.status = AppraisalApprovalAssignment.PENDING
                            prev_assignment.save()

                            # Notify previous reviewer
                            try:
                                Notification.objects.create(
                                    recipient=prev_assignment.approver,
                                    sender=request.user,
                                    notification_type=Notification.APPRAISAL_RETURNED,
                                    title=f"Appraisal Returned to Step {prev_step_number}",
                                    message=(
                                        f"{appraisal.staff.full_name}'s appraisal was returned by "
                                        f"{request.user.full_name} at step {current_step_number}. "
                                        f"Reason: {comments}"
                                    ),
                                    related_appraisal=appraisal,
                                )
                            except Exception:
                                pass

                # Write immutable return log entry (preserved even after re-approval)
                from appraisals.models import AppraisalReturnLog
                try:
                    AppraisalReturnLog.objects.create(
                        appraisal=appraisal,
                        reviewer=request.user,
                        step=assignment.step,
                        from_step_number=current_step_number,
                        to_step_number=to_step_number,
                        reason=comments or '',
                    )
                except Exception:
                    pass

        return Response({
            'message': f'Step review action "{action}" processed successfully.',
            'appraisal': AppraisalDetailSerializer(appraisal, context={'request': request}).data
        })


class ReviewHistoryListView(APIView):
    """
    GET /api/review/history/
    Returns all appraisals the current user has already actioned (APPROVED or RETURNED).
    Used on mobile to show a read-only history of past reviews.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def get(self, request):
        user = request.user

        # Get appraisal IDs that are currently pending for this user at the active step
        # so we can exclude them from history (avoid showing same appraisal in both tabs)
        pending_appraisal_ids = set(
            AppraisalApprovalAssignment.objects.filter(
                approver=user,
                status=AppraisalApprovalAssignment.PENDING,
                appraisal__status__in=[
                    Appraisal.SUBMITTED,
                    Appraisal.AWAITING_STEP_REVIEW,
                    Appraisal.RETURNED_TO_REVIEWER,
                ]
            ).values_list('appraisal_id', flat=True)
        )

        assignments = (
            AppraisalApprovalAssignment.objects
            .filter(
                approver=user,
                status__in=[
                    AppraisalApprovalAssignment.APPROVED,
                    AppraisalApprovalAssignment.RETURNED,
                ]
            )
            .exclude(appraisal_id__in=pending_appraisal_ids)
            .select_related('appraisal', 'appraisal__staff', 'appraisal__cycle', 'step')
            .order_by('-actioned_at')
        )

        history_data = []
        for ass in assignments:
            appraisal = ass.appraisal

            # Include general_step_role_map for consistency with the queue endpoint
            general_process = appraisal.cycle.approval_processes.filter(is_general=True).first()
            general_step_role_map = {}
            if general_process:
                for gstep in general_process.steps.all():
                    general_step_role_map[f'STEP_{gstep.step_number}'] = gstep.role_required

            # Collect roles in active process for smart step resolution
            active_process = appraisal.active_process
            active_process_roles = []
            if active_process:
                active_process_roles = list(
                    active_process.steps.values_list('role_required', flat=True)
                )

            history_data.append({
                'assignment_id': ass.id,
                'step_number': ass.step.step_number,
                'step_label': ass.step.label,
                'role_required': ass.step.role_required,
                'action_label_approve': ass.step.action_label_approve,
                'action_label_return': ass.step.action_label_return,
                'actioned_status': ass.status,          # APPROVED or RETURNED
                'actioned_at': ass.actioned_at.isoformat() if ass.actioned_at else None,
                'comments': ass.comments,
                'appraisal': AppraisalListSerializer(appraisal, context={'request': request}).data,
                'general_step_role_map': general_step_role_map,
                'active_step_number': ass.step.step_number,
                'active_process_roles': active_process_roles,
            })

        return Response(history_data)



class AcknowledgeAppraisalView(APIView):
    """
    POST /api/appraisals/<id>/acknowledge/
    Acknowledge completed appraisal (Staff action).
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def post(self, request, pk):
        appraisal = get_object_or_404(Appraisal, pk=pk, staff=request.user)

        if appraisal.status != Appraisal.APPROVED:
            return Response({'error': 'Only fully approved appraisals can be acknowledged.'}, status=status.HTTP_400_BAD_REQUEST)

        if appraisal.staff_acknowledged_at:
            return Response({'error': 'Appraisal has already been acknowledged.'}, status=status.HTTP_400_BAD_REQUEST)

        appraisal.status = Appraisal.STAFF_ACKNOWLEDGED
        appraisal.staff_acknowledged_at = timezone.now()
        appraisal.save()

        return Response({
            'message': 'Appraisal acknowledged successfully.',
            'appraisal': AppraisalDetailSerializer(appraisal).data
        })


class NotificationsListView(APIView):
    """
    GET /api/notifications/
    Returns notification history for user.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:50]
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class MarkNotificationReadView(APIView):
    """
    PATCH /api/notifications/<id>/read/
    Marks a notification as read.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read.'})


# ----------------------------------------------------
# Helper calculations and workflow handlers
# ----------------------------------------------------

def _calculate_self_score(appraisal):
    total_weight = Decimal('0.00')
    total_score = Decimal('0.00')

    for section in FormSection.objects.filter(cycle=appraisal.cycle):
        weight = section.section_weight
        if not weight:
            continue
        scored_fields = section.fields.filter(field_type__in=[FormField.SCORE, FormField.SCORE_COMMENT])
        if not scored_fields.exists():
            continue

        responses = FormFieldResponse.objects.filter(
            appraisal=appraisal,
            field__in=scored_fields,
            responded_by=appraisal.staff,
            response_type=FormFieldResponse.PRIMARY,
            score__isnull=False
        )
        if not responses.exists():
            continue

        sec_tot = Decimal('0.00')
        sec_max = Decimal('0.00')
        for r in responses:
            sec_tot += r.score or Decimal('0')
            sec_max += r.field.max_score

        if sec_max > 0:
            total_score += (sec_tot / sec_max) * weight
            total_weight += weight

    if total_weight == 0:
        return None
    return total_score.quantize(Decimal('0.01'))


def _calculate_supervisor_score(appraisal):
    total_weight = Decimal('0.00')
    total_score = Decimal('0.00')

    for section in FormSection.objects.filter(cycle=appraisal.cycle):
        weight = section.section_weight
        if not weight:
            continue
        scored_fields = section.fields.filter(field_type__in=[FormField.SCORE, FormField.SCORE_COMMENT])
        if not scored_fields.exists():
            continue

        responses = FormFieldResponse.objects.filter(
            appraisal=appraisal,
            field__in=scored_fields,
            response_type=FormFieldResponse.PRIMARY,
            score__isnull=False
        ).exclude(responded_by=appraisal.staff)

        if not responses.exists():
            continue

        sec_tot = Decimal('0.00')
        sec_max = Decimal('0.00')
        for r in responses:
            sec_tot += r.score or Decimal('0')
            sec_max += r.field.max_score

        if sec_max > 0:
            total_score += (sec_tot / sec_max) * weight
            total_weight += weight

    if total_weight == 0:
        return None
    return total_score.quantize(Decimal('0.01'))


def _setup_and_notify_step_1(appraisal, staff_user):
    process = appraisal.override_process or appraisal.cycle.general_approval_process
    if not process:
        return

    step1 = process.steps.filter(step_number=1).first()
    if not step1:
        return

    assignment, _ = AppraisalApprovalAssignment.objects.get_or_create(
        appraisal=appraisal,
        step=step1,
    )
    if not assignment.approver:
        # Default step 1 approver to staff's supervisor if role is SUPERVISOR
        if step1.role_required == ApprovalStep.SUPERVISOR and staff_user.supervisor:
            assignment.approver = staff_user.supervisor
            assignment.save()

    if assignment.approver:
        assignment.status = AppraisalApprovalAssignment.PENDING
        assignment.save()
        try:
            Notification.objects.create(
                recipient=assignment.approver,
                sender=staff_user,
                notification_type=Notification.APPRAISAL_SUBMITTED,
                title="New Appraisal Submitted for Review",
                message=f"{staff_user.full_name} has submitted their self-appraisal for {appraisal.cycle.name}.",
                related_appraisal=appraisal,
            )
        except Exception:
            pass


def _advance_workflow(appraisal, current_assignment, actioning_user):
    process = appraisal.override_process or appraisal.cycle.general_approval_process
    if not process:
        appraisal.status = Appraisal.APPROVED
        appraisal.save()
        return

    next_step_num = current_assignment.step.step_number + 1
    next_step = process.steps.filter(step_number=next_step_num).first()

    if not next_step:
        appraisal.status = Appraisal.APPROVED
        appraisal.save()
        try:
            Notification.objects.create(
                recipient=appraisal.staff,
                sender=actioning_user,
                notification_type=Notification.APPRAISAL_APPROVED,
                title="Appraisal Fully Approved",
                message=f"Your appraisal for {appraisal.cycle.name} has been fully approved.",
                related_appraisal=appraisal,
            )
        except Exception:
            pass
    else:
        appraisal.current_step_number = next_step_num
        appraisal.status = Appraisal.AWAITING_STEP_REVIEW
        appraisal.save()

        next_assignment = appraisal.approval_assignments.filter(step=next_step).first()
        if next_assignment and next_assignment.approver:
            next_assignment.status = AppraisalApprovalAssignment.PENDING
            next_assignment.save()
            try:
                Notification.objects.create(
                    recipient=next_assignment.approver,
                    sender=actioning_user,
                    notification_type=Notification.APPRAISAL_REVIEWED,
                    title=f"Appraisal Awaiting Your Review — Step {next_step_num}",
                    message=f"{appraisal.staff.full_name}'s appraisal is now awaiting your action at step {next_step_num}: {next_step.label}.",
                    related_appraisal=appraisal,
                )
            except Exception:
                pass


# ------------------------------------------------------------------
# HR Administration API Views
# ------------------------------------------------------------------

class HRDashboardView(APIView):
    """
    GET /api/hr/dashboard/
    Returns HR Administration overview metrics and department statistics.
    """
    permission_classes = [permissions.IsAuthenticated, IsHRAdmin]

    def get(self, request):
        total_staff = User.objects.filter(is_active=True).count()
        total_departments = Department.objects.count()
        total_branches = Branch.objects.count()

        active_cycles = AppraisalCycle.objects.filter(status=AppraisalCycle.ACTIVE)
        active_cycles_count = active_cycles.count()

        total_appraisals = Appraisal.objects.count()
        completed_appraisals = Appraisal.objects.filter(
            status__in=[Appraisal.APPROVED, Appraisal.STAFF_ACKNOWLEDGED]
        ).count()
        pending_reviews = Appraisal.objects.filter(
            status__in=[Appraisal.SUBMITTED, Appraisal.AWAITING_STEP_REVIEW, Appraisal.RETURNED_TO_REVIEWER]
        ).count()

        # Department breakdown
        dept_stats = []
        departments = Department.objects.all()
        for dept in departments:
            staff_count = User.objects.filter(department=dept, is_active=True).count()
            dept_appraisals = Appraisal.objects.filter(staff__department=dept)
            dept_completed = dept_appraisals.filter(
                status__in=[Appraisal.APPROVED, Appraisal.ACKNOWLEDGED]
            ).count()
            dept_pending = dept_appraisals.filter(
                status__in=[Appraisal.SUBMITTED, Appraisal.AWAITING_STEP_REVIEW, Appraisal.RETURNED_TO_REVIEWER]
            ).count()

            dept_stats.append({
                'id': dept.id,
                'name': dept.name,
                'code': dept.code,
                'staff_count': staff_count,
                'total_appraisals': dept_appraisals.count(),
                'completed_appraisals': dept_completed,
                'pending_reviews': dept_pending,
            })

        return Response({
            'total_staff': total_staff,
            'total_departments': total_departments,
            'total_branches': total_branches,
            'active_cycles_count': active_cycles_count,
            'total_appraisals': total_appraisals,
            'completed_appraisals': completed_appraisals,
            'pending_reviews': pending_reviews,
            'department_stats': dept_stats,
        })


class HRStaffListView(APIView):
    """
    GET /api/hr/staff/
    Returns list of staff members with optional search, department, branch, and role filtering.
    """
    permission_classes = [permissions.IsAuthenticated, IsHRAdmin]

    def get(self, request):
        qs = User.objects.filter(is_active=True).select_related('department', 'supervisor')

        search = request.GET.get('search', '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(staff_id__icontains=search) |
                Q(email__icontains=search)
            )

        department_id = request.GET.get('department_id')
        if department_id:
            qs = qs.filter(department_id=department_id)

        role = request.GET.get('role')
        if role:
            qs = qs.filter(role=role)

        serializer = UserSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class HRDepartmentsListView(APIView):
    """
    GET /api/hr/departments/
    Returns list of departments with staff count and HOD info.
    """
    permission_classes = [permissions.IsAuthenticated, IsHRAdmin]

    def get(self, request):
        departments = Department.objects.all()
        result = []
        for dept in departments:
            staff_count = User.objects.filter(department=dept, is_active=True).count()
            hod_user = User.objects.filter(department=dept, role=User.HOD).first()
            result.append({
                'id': dept.id,
                'name': dept.name,
                'code': dept.code,
                'staff_count': staff_count,
                'hod_name': hod_user.full_name if hod_user else 'Not Assigned',
            })
        return Response(result)


class HRBranchesListView(APIView):
    """
    GET /api/hr/branches/
    Returns list of branches with staff count.
    """
    permission_classes = [permissions.IsAuthenticated, IsHRAdmin]

    def get(self, request):
        branches = Branch.objects.all()
        result = []
        for branch in branches:
            staff_count = User.objects.filter(branch=branch, is_active=True).count()
            result.append({
                'id': branch.id,
                'name': branch.name,
                'code': branch.code,
                'staff_count': staff_count,
            })
        return Response(result)


class HRReportsView(APIView):
    """
    GET /api/hr/reports/
    Returns appraisal analytics summary.
    """
    permission_classes = [permissions.IsAuthenticated, IsHRAdmin]

    def get(self, request):
        total = Appraisal.objects.count()
        draft = Appraisal.objects.filter(status=Appraisal.DRAFT).count()
        submitted = Appraisal.objects.filter(status=Appraisal.SUBMITTED).count()
        in_review = Appraisal.objects.filter(
            status__in=[Appraisal.AWAITING_STEP_REVIEW, Appraisal.RETURNED_TO_REVIEWER]
        ).count()
        approved = Appraisal.objects.filter(status=Appraisal.APPROVED).count()
        acknowledged = Appraisal.objects.filter(status=Appraisal.ACKNOWLEDGED).count()
        completed = approved + acknowledged

        completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

        dept_performance = []
        for dept in Department.objects.all():
            dept_appraisals = Appraisal.objects.filter(staff__department=dept)
            dept_total = dept_appraisals.count()
            dept_completed = dept_appraisals.filter(
                status__in=[Appraisal.APPROVED, Appraisal.ACKNOWLEDGED]
            ).count()
            rate = round((dept_completed / dept_total * 100), 1) if dept_total > 0 else 0.0
            dept_performance.append({
                'department_name': dept.name,
                'total': dept_total,
                'completed': dept_completed,
                'completion_rate': rate,
            })

        return Response({
            'total_appraisals': total,
            'draft': draft,
            'submitted': submitted,
            'in_review': in_review,
            'completed': completed,
            'completion_rate': completion_rate,
            'department_performance': dept_performance,
        })


class FormFieldEvidenceUploadView(APIView):
    """
    POST /api/appraisals/<id>/evidence/
    Upload an evidence file for a specific form field response.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotHRAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        appraisal = get_object_or_404(Appraisal, pk=pk, staff=request.user)

        if appraisal.status not in [Appraisal.NOT_STARTED, Appraisal.DRAFT, Appraisal.RETURNED_TO_STAFF]:
            return Response({'error': 'Cannot upload evidence for this appraisal at this stage.'}, status=status.HTTP_400_BAD_REQUEST)

        field_id = request.data.get('field_id')
        file_obj = request.FILES.get('file')

        if not field_id or not file_obj:
            return Response({'error': 'Both field_id and file are required.'}, status=status.HTTP_400_BAD_REQUEST)

        field = get_object_or_404(FormField, id=field_id, section__cycle=appraisal.cycle)

        resp_obj, _ = FormFieldResponse.objects.get_or_create(
            appraisal=appraisal,
            field=field,
            responded_by=request.user,
            response_type=FormFieldResponse.PRIMARY,
        )

        resp_obj.evidence_file = file_obj
        resp_obj.save()

        url = resp_obj.evidence_file.url
        if not (url.startswith('http://') or url.startswith('https://')):
            url = request.build_absolute_uri(url)

        return Response({
            'message': 'Evidence file uploaded successfully.',
            'field_id': field.id,
            'evidence_file_url': url,
        })


class AppraisalReturnHistoryView(APIView):
    """
    GET /api/appraisals/<pk>/return-history/
    Returns all return log entries for an appraisal, ordered newest first.
    Each entry includes the reviewer name, step info, reason text, and timestamp.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        appraisal = get_object_or_404(Appraisal, pk=pk)

        # Staff can see their own; reviewers assigned to this appraisal can see it
        is_staff_owner = appraisal.staff == request.user
        is_reviewer = appraisal.approval_assignments.filter(approver=request.user).exists()
        is_hr = request.user.role in [CustomUser.HR_ADMIN]
        if not (is_staff_owner or is_reviewer or is_hr):
            return Response({'detail': 'Permission denied.'}, status=403)

        logs = AppraisalReturnLog.objects.filter(appraisal=appraisal).select_related(
            'reviewer', 'step'
        ).order_by('-returned_at')

        data = []
        for log in logs:
            reviewer_name = log.reviewer.get_full_name() if log.reviewer else 'Unknown'
            step_label = log.step.label if log.step else f'Step {log.from_step_number}'
            to_label = 'Staff (Re-fill)' if log.to_step_number == 0 else f'Step {log.to_step_number}'
            data.append({
                'id': log.id,
                'reviewer_name': reviewer_name,
                'step_label': step_label,
                'from_step_number': log.from_step_number,
                'to_step_number': log.to_step_number,
                'to_label': to_label,
                'reason': log.reason,
                'returned_at': log.returned_at.isoformat(),
            })

        return Response({'return_history': data})


