import '../core/parse_helpers.dart';
import 'form_model.dart';
import 'user_model.dart';

class AppraisalCycleModel {
  final int id;
  final String name;
  final String frequency;
  final String startDate;
  final String endDate;
  final String status;
  final int scoringScale;

  AppraisalCycleModel({
    required this.id,
    required this.name,
    required this.frequency,
    required this.startDate,
    required this.endDate,
    required this.status,
    required this.scoringScale,
  });

  factory AppraisalCycleModel.fromJson(Map<String, dynamic> json) {
    return AppraisalCycleModel(
      id: json['id'],
      name: json['name'] ?? '',
      frequency: json['frequency'] ?? 'ANNUAL',
      startDate: json['start_date'] ?? '',
      endDate: json['end_date'] ?? '',
      status: json['status'] ?? 'DRAFT',
      scoringScale: parseInt(json['scoring_scale']) ?? 5,
    );
  }
}

class ApprovalStepModel {
  final int id;
  final int stepNumber;
  final String label;
  final String roleRequired;
  final String roleRequiredDisplay;
  final String actionLabelApprove;
  final String actionLabelReturn;
  final bool canScore;

  ApprovalStepModel({
    required this.id,
    required this.stepNumber,
    required this.label,
    required this.roleRequired,
    required this.roleRequiredDisplay,
    required this.actionLabelApprove,
    required this.actionLabelReturn,
    required this.canScore,
  });

  factory ApprovalStepModel.fromJson(Map<String, dynamic> json) {
    return ApprovalStepModel(
      id: json['id'],
      stepNumber: parseInt(json['step_number']) ?? 1,
      label: json['label'] ?? '',
      roleRequired: json['role_required'] ?? 'SUPERVISOR',
      roleRequiredDisplay: json['role_required_display'] ?? '',
      actionLabelApprove: json['action_label_approve'] ?? 'Approve & Forward',
      actionLabelReturn: json['action_label_return'] ?? 'Return for Revision',
      canScore: json['can_score'] ?? true,
    );
  }
}

class ApprovalAssignmentModel {
  final int id;
  final ApprovalStepModel? step;
  final int? approver;
  final String? approverName;
  final String status; // PENDING, APPROVED, RETURNED, SKIPPED
  final String comments;
  final String? actionedAt;

  ApprovalAssignmentModel({
    required this.id,
    this.step,
    this.approver,
    this.approverName,
    required this.status,
    required this.comments,
    this.actionedAt,
  });

  factory ApprovalAssignmentModel.fromJson(Map<String, dynamic> json) {
    return ApprovalAssignmentModel(
      id: json['id'],
      step: json['step'] != null ? ApprovalStepModel.fromJson(json['step']) : null,
      approver: json['approver'],
      approverName: json['approver_name'],
      status: json['status'] ?? 'PENDING',
      comments: json['comments'] ?? '',
      actionedAt: json['actioned_at'],
    );
  }
}

class AppraisalItemModel {
  final int id;
  final int cycle;
  final String cycleName;
  final int staff;
  final String staffName;
  final String staffId;
  final String? departmentName;
  final String status;
  final String statusDisplay;
  final int currentStepNumber;
  final String? selfSubmittedAt;
  final double? overallSelfScore;
  final double? overallSupervisorScore;
  final String? staffProfilePictureUrl;
  final String? returnNotes;

  AppraisalItemModel({
    required this.id,
    required this.cycle,
    required this.cycleName,
    required this.staff,
    required this.staffName,
    required this.staffId,
    this.departmentName,
    required this.status,
    required this.statusDisplay,
    required this.currentStepNumber,
    this.selfSubmittedAt,
    this.overallSelfScore,
    this.overallSupervisorScore,
    this.staffProfilePictureUrl,
    this.returnNotes,
  });

  factory AppraisalItemModel.fromJson(Map<String, dynamic> json) {
    return AppraisalItemModel(
      id: json['id'],
      cycle: json['cycle'] ?? 0,
      cycleName: json['cycle_name'] ?? '',
      staff: json['staff'] ?? 0,
      staffName: json['staff_name'] ?? '',
      staffId: json['staff_id'] ?? '',
      departmentName: json['department_name'],
      status: json['status'] ?? 'NOT_STARTED',
      statusDisplay: json['status_display'] ?? '',
      currentStepNumber: json['current_step_number'] ?? 0,
      selfSubmittedAt: json['self_submitted_at'],
      // DRF DecimalField — comes as String
      overallSelfScore: parseDouble(json['overall_self_score']),
      overallSupervisorScore: parseDouble(json['overall_supervisor_score']),
      staffProfilePictureUrl: json['staff_profile_picture_url'],
      returnNotes: json['return_notes'] ?? json['supervisor_return_notes'] ?? json['hod_return_notes'],
    );
  }
}

class AppraisalDetailModel {
  final int id;
  final AppraisalCycleModel cycle;
  final UserModel staff;
  final String status;
  final String statusDisplay;
  final int currentStepNumber;
  final String? selfSubmittedAt;
  final String? supervisorReviewedAt;
  final String? staffAcknowledgedAt;
  final double? overallSelfScore;
  final double? overallSupervisorScore;
  final List<ApprovalAssignmentModel> approvalAssignments;
  final List<FormFieldResponseModel> formResponses;
  final List<FormSectionModel> sections;
  // Server-computed convenience flags
  final bool canEdit;
  final bool canAcknowledge;
  final String? returnNotes;

  AppraisalDetailModel({
    required this.id,
    required this.cycle,
    required this.staff,
    required this.status,
    required this.statusDisplay,
    required this.currentStepNumber,
    this.selfSubmittedAt,
    this.supervisorReviewedAt,
    this.staffAcknowledgedAt,
    this.overallSelfScore,
    this.overallSupervisorScore,
    required this.approvalAssignments,
    required this.formResponses,
    required this.sections,
    required this.canEdit,
    required this.canAcknowledge,
    this.returnNotes,
  });

  factory AppraisalDetailModel.fromJson(Map<String, dynamic> json) {
    return AppraisalDetailModel(
      id: json['id'],
      cycle: AppraisalCycleModel.fromJson(json['cycle']),
      staff: UserModel.fromJson(json['staff']),
      status: json['status'] ?? 'NOT_STARTED',
      statusDisplay: json['status_display'] ?? '',
      currentStepNumber: json['current_step_number'] ?? 0,
      selfSubmittedAt: json['self_submitted_at'],
      supervisorReviewedAt: json['supervisor_reviewed_at'],
      staffAcknowledgedAt: json['staff_acknowledged_at'],
      // DRF DecimalField — comes as String
      overallSelfScore: parseDouble(json['overall_self_score']),
      overallSupervisorScore: parseDouble(json['overall_supervisor_score']),
      approvalAssignments: (json['approval_assignments'] as List?)
              ?.map((e) => ApprovalAssignmentModel.fromJson(e))
              .toList() ??
          [],
      formResponses: (json['form_responses'] as List?)
              ?.map((e) => FormFieldResponseModel.fromJson(e))
              .toList() ??
          [],
      sections: (json['sections'] as List?)
              ?.map((e) => FormSectionModel.fromJson(e))
              .toList() ??
          [],
      // Use server-provided flags with client-side fallback
      canEdit: json['can_edit'] ??
          ['NOT_STARTED', 'DRAFT', 'RETURNED_TO_STAFF']
              .contains(json['status'] ?? ''),
      canAcknowledge: json['can_acknowledge'] ??
          (json['status'] == 'APPROVED' && json['staff_acknowledged_at'] == null),
      returnNotes: json['return_notes'],
    );
  }
}
