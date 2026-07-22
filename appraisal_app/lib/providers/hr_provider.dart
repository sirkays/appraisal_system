import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../models/user_model.dart';

class HrProvider extends ChangeNotifier {
  final ApiService _api = ApiService();

  Map<String, dynamic>? _dashboardData;
  List<UserModel> _staffList = [];
  List<Map<String, dynamic>> _departments = [];
  List<Map<String, dynamic>> _branches = [];
  Map<String, dynamic>? _reportsData;

  bool _isLoadingDashboard = false;
  bool _isLoadingStaff = false;
  bool _isLoadingDepartments = false;
  bool _isLoadingBranches = false;
  bool _isLoadingReports = false;

  String? _errorMessage;

  Map<String, dynamic>? get dashboardData => _dashboardData;
  List<UserModel> get staffList => _staffList;
  List<Map<String, dynamic>> get departments => _departments;
  List<Map<String, dynamic>> get branches => _branches;
  Map<String, dynamic>? get reportsData => _reportsData;

  bool get isLoadingDashboard => _isLoadingDashboard;
  bool get isLoadingStaff => _isLoadingStaff;
  bool get isLoadingDepartments => _isLoadingDepartments;
  bool get isLoadingBranches => _isLoadingBranches;
  bool get isLoadingReports => _isLoadingReports;

  String? get errorMessage => _errorMessage;

  Future<void> fetchHrDashboard() async {
    _isLoadingDashboard = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.get('/hr/dashboard/');
      _dashboardData = res is Map<String, dynamic> ? res : {};
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoadingDashboard = false;
      notifyListeners();
    }
  }

  Future<void> fetchStaff({String search = '', int? departmentId, String? role}) async {
    _isLoadingStaff = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final params = <String>[];
      if (search.isNotEmpty) params.add('search=${Uri.encodeComponent(search)}');
      if (departmentId != null) params.add('department_id=$departmentId');
      if (role != null && role.isNotEmpty) params.add('role=$role');

      final query = params.isNotEmpty ? '?${params.join('&')}' : '';
      final res = await _api.get('/hr/staff/$query');
      if (res is List) {
        _staffList = res.map((item) => UserModel.fromJson(item)).toList();
      } else {
        _staffList = [];
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoadingStaff = false;
      notifyListeners();
    }
  }

  Future<void> fetchDepartments() async {
    _isLoadingDepartments = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.get('/hr/departments/');
      if (res is List) {
        _departments = List<Map<String, dynamic>>.from(res);
      } else {
        _departments = [];
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoadingDepartments = false;
      notifyListeners();
    }
  }

  Future<void> fetchBranches() async {
    _isLoadingBranches = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.get('/hr/branches/');
      if (res is List) {
        _branches = List<Map<String, dynamic>>.from(res);
      } else {
        _branches = [];
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoadingBranches = false;
      notifyListeners();
    }
  }

  Future<void> fetchReports() async {
    _isLoadingReports = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.get('/hr/reports/');
      _reportsData = res is Map<String, dynamic> ? res : {};
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoadingReports = false;
      notifyListeners();
    }
  }
}
