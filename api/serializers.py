from rest_framework import serializers
from django.contrib.auth import get_user_model
from appraisals.models import (
    AppraisalCycle, Appraisal, ApprovalProcess, ApprovalStep,
    AppraisalApprovalAssignment, FormSection, FormField, FormFieldResponse
)
from departments.models import Department
from branches.models import Branch
from notifications.models import Notification

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'code']


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'code']


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.full_name', read_only=True)
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'staff_id', 'role', 'designation', 'phone',
            'department', 'department_name', 'supervisor', 'supervisor_name',
            'profile_picture', 'profile_picture_url'
        ]

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            try:
                url = obj.profile_picture.url
                if url.startswith('http://') or url.startswith('https://'):
                    return url
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return str(obj.profile_picture)
        return None


class AppraisalCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalCycle
        fields = [
            'id', 'name', 'frequency', 'start_date', 'end_date',
            'status', 'scoring_scale'
        ]


class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = [
            'id', 'label', 'description', 'field_type', 'filled_by',
            'max_score', 'min_score', 'options',
            'reviewer_can_score', 'reviewer_score_role', 'reviewer_score_max',
            'reviewer_can_comment', 'reviewer_comment_role',
            'is_required', 'order'
        ]


class FormSectionSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = FormSection
        fields = [
            'id', 'name', 'description', 'section_weight', 'order', 'fields'
        ]


class FormFieldResponseSerializer(serializers.ModelSerializer):
    field_id = serializers.IntegerField(source='field.id')
    responded_by_name = serializers.CharField(source='responded_by.full_name', read_only=True)
    evidence_file_url = serializers.SerializerMethodField()

    class Meta:
        model = FormFieldResponse
        fields = [
            'id', 'field_id', 'responded_by', 'responded_by_name',
            'response_type', 'text_response', 'score', 'selected_options',
            'evidence_file_url', 'responded_at'
        ]

    def get_evidence_file_url(self, obj):
        if obj.evidence_file:
            try:
                url = obj.evidence_file.url
                if url.startswith('http://') or url.startswith('https://'):
                    return url
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return str(obj.evidence_file)
        return None


class ApprovalStepSerializer(serializers.ModelSerializer):
    role_required_display = serializers.CharField(source='get_role_required_display', read_only=True)

    class Meta:
        model = ApprovalStep
        fields = [
            'id', 'step_number', 'label', 'role_required',
            'role_required_display', 'action_label_approve',
            'action_label_return', 'can_score'
        ]


class ApprovalAssignmentSerializer(serializers.ModelSerializer):
    step = ApprovalStepSerializer(read_only=True)
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)

    class Meta:
        model = AppraisalApprovalAssignment
        fields = [
            'id', 'step', 'approver', 'approver_name',
            'status', 'comments', 'actioned_at'
        ]


class AppraisalListSerializer(serializers.ModelSerializer):
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    staff_id = serializers.CharField(source='staff.staff_id', read_only=True)
    department_name = serializers.CharField(source='staff.department.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    staff_profile_picture_url = serializers.SerializerMethodField()
    return_notes = serializers.SerializerMethodField()

    class Meta:
        model = Appraisal
        fields = [
            'id', 'cycle', 'cycle_name', 'staff', 'staff_name', 'staff_id',
            'department_name', 'status', 'status_display',
            'current_step_number', 'self_submitted_at',
            'overall_self_score', 'overall_supervisor_score',
            'staff_profile_picture_url', 'return_notes',
            'supervisor_return_notes', 'hod_return_notes'
        ]

    def get_return_notes(self, obj):
        notes = getattr(obj, 'supervisor_return_notes', '') or ''
        hod_notes = getattr(obj, 'hod_return_notes', '') or ''
        combined = hod_notes.strip() or notes.strip()
        return combined if combined else None

    def get_staff_profile_picture_url(self, obj):
        if obj.staff and obj.staff.profile_picture:
            try:
                url = obj.staff.profile_picture.url
                if url.startswith('http://') or url.startswith('https://'):
                    return url
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return str(obj.staff.profile_picture)
        return None


class AppraisalDetailSerializer(serializers.ModelSerializer):
    cycle = AppraisalCycleSerializer(read_only=True)
    staff = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approval_assignments = ApprovalAssignmentSerializer(many=True, read_only=True)
    form_responses = FormFieldResponseSerializer(many=True, read_only=True)
    sections = serializers.SerializerMethodField(method_name='get_sections')
    can_edit = serializers.SerializerMethodField()
    can_acknowledge = serializers.SerializerMethodField()
    return_notes = serializers.SerializerMethodField()

    class Meta:
        model = Appraisal
        fields = [
            'id', 'cycle', 'staff', 'status', 'status_display',
            'current_step_number', 'self_submitted_at',
            'supervisor_reviewed_at', 'staff_acknowledged_at',
            'overall_self_score', 'overall_supervisor_score',
            'approval_assignments', 'form_responses', 'sections',
            'can_edit', 'can_acknowledge', 'return_notes',
        ]

    def get_sections(self, obj):
        sections = FormSection.objects.filter(cycle=obj.cycle).prefetch_related('fields')
        return FormSectionSerializer(sections, many=True).data

    def get_can_edit(self, obj):
        """True when the staff member can still fill/edit the form."""
        return obj.status in [
            Appraisal.NOT_STARTED, Appraisal.DRAFT, Appraisal.RETURNED_TO_STAFF
        ]

    def get_can_acknowledge(self, obj):
        """True when the appraisal is fully approved and not yet acknowledged."""
        return obj.status == Appraisal.APPROVED and not obj.staff_acknowledged_at

    def get_return_notes(self, obj):
        """Return the most relevant return reason text when the appraisal was sent back."""
        # 1. Check if any step assignment was marked RETURNED with comments
        returned_ass = obj.approval_assignments.filter(status='RETURNED').order_by('-actioned_at').first()
        if returned_ass and returned_ass.comments:
            return returned_ass.comments.strip()

        # 2. Check legacy/field return notes
        hod_notes = (getattr(obj, 'hod_return_notes', '') or '').strip()
        notes = (getattr(obj, 'supervisor_return_notes', '') or '').strip()
        
        combined = hod_notes or notes
        return combined if combined else None


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at']
