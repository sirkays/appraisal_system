import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../models/appraisal_model.dart';

class ReviewQueueItem {
  final int assignmentId;
  final int stepNumber;
  final String stepLabel;
  final String roleRequired;
  final String actionLabelApprove;
  final String actionLabelReturn;
  final AppraisalItemModel appraisal;
  final Map<String, String> generalStepRoleMap;
  final int? activeStepNumber;
  final List<String> activeProcessRoles;

  // History-only fields (null for pending queue items)
  final String? actionedStatus; // 'APPROVED' or 'RETURNED'
  final String? actionedAt;
  final String? comments;

  ReviewQueueItem({
    required this.assignmentId,
    required this.stepNumber,
    required this.stepLabel,
    required this.roleRequired,
    required this.actionLabelApprove,
    required this.actionLabelReturn,
    required this.appraisal,
    this.generalStepRoleMap = const {},
    this.activeStepNumber,
    this.activeProcessRoles = const [],
    this.actionedStatus,
    this.actionedAt,
    this.comments,
  });

  bool get isHistoryItem => actionedStatus != null;

  /// Returns all filled_by values this reviewer can fill.
  /// Includes:
  ///   1. Direct role code (e.g. 'HOD')
  ///   2. STEP_N from the GENERAL process where the role matches
  ///   3. STEP_N from the active step number, only if the general process's
  ///      role at that step isn't a separate reviewer in the active process
  List<String> get allowedFilledByValues {
    final values = <String>{roleRequired};
    // Include STEP_N codes from the general process where the role matches
    generalStepRoleMap.forEach((stepCode, role) {
      if (role == roleRequired) {
        values.add(stepCode);
      }
    });
    // Smart active step inclusion
    if (activeStepNumber != null) {
      final activeStepCode = 'STEP_$activeStepNumber';
      final generalRoleAtStep = generalStepRoleMap[activeStepCode];
      if (generalRoleAtStep == null || generalRoleAtStep == roleRequired) {
        // Same role or step doesn't exist in general -> always include
        values.add(activeStepCode);
      } else if (!activeProcessRoles.contains(generalRoleAtStep)) {
        // General role at this step is absent from active process
        // -> this reviewer absorbs those duties
        values.add(activeStepCode);
      }
    }
    return values.where((v) => v.isNotEmpty).toList();
  }

  factory ReviewQueueItem.fromJson(Map<String, dynamic> json) {
    final rawMap = json['general_step_role_map'];
    final Map<String, String> stepRoleMap = {};
    if (rawMap is Map) {
      rawMap.forEach((key, value) {
        stepRoleMap[key.toString()] = value.toString();
      });
    }

    return ReviewQueueItem(
      assignmentId: json['assignment_id'],
      stepNumber: json['step_number'],
      stepLabel: json['step_label'] ?? '',
      roleRequired: json['role_required'] ?? '',
      actionLabelApprove: json['action_label_approve'] ?? 'Approve & Forward',
      actionLabelReturn: json['action_label_return'] ?? 'Return for Revision',
      appraisal: AppraisalItemModel.fromJson(json['appraisal']),
      generalStepRoleMap: stepRoleMap,
      activeStepNumber: json['active_step_number'],
      activeProcessRoles: (json['active_process_roles'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList() ?? [],
      actionedStatus: json['actioned_status'],
      actionedAt: json['actioned_at'],
      comments: json['comments'],
    );
  }
}

class ReviewerProvider extends ChangeNotifier {
  final ApiService _api = ApiService();

  List<ReviewQueueItem> _queue = [];
  List<ReviewQueueItem> _history = [];
  bool _isLoading = false;
  bool _isHistoryLoading = false;
  String? _errorMessage;

  List<ReviewQueueItem> get queue => _queue;
  List<ReviewQueueItem> get history => _history;
  bool get isLoading => _isLoading;
  bool get isHistoryLoading => _isHistoryLoading;
  String? get errorMessage => _errorMessage;

  Future<void> fetchQueue() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.get('/review/queue/');
      _queue = (res as List).map((e) => ReviewQueueItem.fromJson(e)).toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchHistory() async {
    _isHistoryLoading = true;
    notifyListeners();

    try {
      final res = await _api.get('/review/history/');
      _history = (res as List).map((e) => ReviewQueueItem.fromJson(e)).toList();
      _isHistoryLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isHistoryLoading = false;
      notifyListeners();
    }
  }

  Future<bool> submitStepReview({
    required int appraisalId,
    required String action, // APPROVE, RETURN, or SAVE_DRAFT
    required String comments,
    required List<Map<String, dynamic>> responses,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _api.post('/review/$appraisalId/step/', {
        'action': action,
        'comments': comments,
        'responses': responses,
      });

      // Refresh both queue and history after a real action
      if (action != 'SAVE_DRAFT') {
        await fetchQueue();
        fetchHistory(); // fire and forget — no await needed
      }
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }
}
