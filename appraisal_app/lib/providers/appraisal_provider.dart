import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../models/appraisal_model.dart';

class AppraisalProvider extends ChangeNotifier {
  final ApiService _api = ApiService();

  Map<String, dynamic>? _dashboardData;
  List<AppraisalItemModel> _myAppraisals = [];
  AppraisalDetailModel? _activeAppraisalDetail;
  List<AppraisalCycleModel> _eligibleCycles = [];
  int? _selectedCycleId;
  bool _isLoading = false;
  bool _isStarting = false;
  String? _errorMessage;

  Map<String, dynamic>? get dashboardData => _dashboardData;
  List<AppraisalItemModel> get myAppraisals => _myAppraisals;
  AppraisalDetailModel? get activeAppraisalDetail => _activeAppraisalDetail;
  List<AppraisalCycleModel> get eligibleCycles => _eligibleCycles;
  int? get selectedCycleId => _selectedCycleId;
  bool get isLoading => _isLoading;
  bool get isStarting => _isStarting;
  String? get errorMessage => _errorMessage;

  Future<void> fetchDashboard() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final endpoint = _selectedCycleId != null
          ? '/dashboard/?cycle_id=$_selectedCycleId'
          : '/dashboard/';
      final res = await _api.get(endpoint);
      _dashboardData = res;
      // Keep selected cycle in sync with what the dashboard returned
      final cycleData = res['active_cycle'];
      if (cycleData != null && _selectedCycleId == null) {
        _selectedCycleId = cycleData['id'];
      }
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetch all active cycles the user is eligible for (powers the cycle switcher).
  Future<void> fetchEligibleCycles() async {
    try {
      final res = await _api.get('/cycles/');
      _eligibleCycles = (res as List)
          .map((e) => AppraisalCycleModel.fromJson(e))
          .toList();
      notifyListeners();
    } catch (_) {
      // Non-critical — silently ignore
    }
  }

  /// Switch the active cycle and reload the dashboard.
  Future<void> switchCycle(int cycleId) async {
    _selectedCycleId = cycleId;
    notifyListeners();
    await fetchDashboard();
  }

  Future<void> fetchMyAppraisals() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.get('/appraisals/my/');
      _myAppraisals = (res as List)
          .map((e) => AppraisalItemModel.fromJson(e))
          .toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchAppraisalDetail(int id) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.get('/appraisals/$id/');
      _activeAppraisalDetail = AppraisalDetailModel.fromJson(res);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Creates or fetches the appraisal for the given (or default) cycle.
  /// Returns the appraisal ID on success, null on failure.
  Future<int?> startAppraisal({int? cycleId}) async {
    _isStarting = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final body = cycleId != null ? {'cycle_id': cycleId} : <String, dynamic>{};
      final res = await _api.post('/appraisals/start/', body);
      final appraisal = AppraisalDetailModel.fromJson(res['appraisal']);
      _activeAppraisalDetail = appraisal;
      _isStarting = false;
      notifyListeners();
      return appraisal.id;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isStarting = false;
      notifyListeners();
      return null;
    }
  }

  Future<bool> submitSelfAppraisal(
      int appraisalId, String action, List<Map<String, dynamic>> responses) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.post('/appraisals/$appraisalId/self-submit/', {
        'action': action,
        'responses': responses,
      });

      _activeAppraisalDetail = AppraisalDetailModel.fromJson(res['appraisal']);
      await fetchDashboard();
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

  Future<bool> acknowledgeAppraisal(int appraisalId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.post('/appraisals/$appraisalId/acknowledge/', {});
      _activeAppraisalDetail = AppraisalDetailModel.fromJson(res['appraisal']);
      await fetchMyAppraisals();
      await fetchDashboard();
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
