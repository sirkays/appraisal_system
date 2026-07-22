import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../core/biometric_service.dart';
import '../models/user_model.dart';

class AuthProvider extends ChangeNotifier {
  final ApiService _api = ApiService();

  UserModel? _user;
  bool _isLoading = false;
  bool _isInitializing = true;
  String? _errorMessage;

  UserModel? get user => _user;
  bool get isLoading => _isLoading;
  bool get isInitializing => _isInitializing;
  bool get isAuthenticated => _user != null;
  String? get errorMessage => _errorMessage;

  Future<void> init() async {
    _isInitializing = true;
    notifyListeners();
    try {
      final token = await _api.token;
      if (token != null && token.isNotEmpty) {
        final res = await _api.get('/me/');
        _user = UserModel.fromJson(res);
      }
    } catch (e) {
      _user = null;
      await _api.setToken(null);
    } finally {
      _isInitializing = false;
      notifyListeners();
    }
  }

  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.post('/auth/login/', {
        'username': username,
        'password': password,
      });

      final token = res['token'];
      await _api.setToken(token);

      final bioService = BiometricService();
      if (await bioService.isBiometricEnabled()) {
        await bioService.saveToken(token);
      }

      _user = UserModel.fromJson(res['user']);
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

  Future<bool> loginWithBiometrics() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final bioService = BiometricService();
      final token = await bioService.getSavedToken();
      
      if (token == null || token.isEmpty) {
        throw Exception('No saved credentials for biometric login.');
      }

      final authenticated = await bioService.authenticate();
      if (!authenticated) {
        _isLoading = false;
        notifyListeners();
        return false; // User cancelled or failed
      }

      // Use the saved token
      await _api.setToken(token);
      final res = await _api.get('/me/');
      
      _user = UserModel.fromJson(res);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      // If token is expired or invalid, clear it
      await _api.setToken(null);
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> fetchCurrentUser() async {
    try {
      final res = await _api.get('/me/');
      _user = UserModel.fromJson(res);
      notifyListeners();
    } catch (e) {
      _user = null;
      await _api.setToken(null);
      notifyListeners();
    }
  }

  Future<bool> updateProfileInfo({
    required String firstName,
    required String lastName,
    required String email,
    required String phone,
    required String designation,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.patch('/me/', {
        'first_name': firstName,
        'last_name': lastName,
        'email': email,
        'phone': phone,
        'designation': designation,
      });
      _user = UserModel.fromJson(res['user']);
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

  Future<bool> updateProfilePicture(String imagePath) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.uploadMultipart('/me/avatar/', imagePath, fieldName: 'profile_picture');
      _user = UserModel.fromJson(res['user']);
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

  Future<bool> changePassword({
    required String currentPassword,
    required String newPassword,
    required String confirmPassword,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _api.post('/auth/change-password/', {
        'current_password': currentPassword,
        'new_password': newPassword,
        'confirm_password': confirmPassword,
      });

      if (res['token'] != null) {
        await _api.setToken(res['token']);
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

  Future<void> logout() async {
    try {
      final bioService = BiometricService();
      final bioEnabled = await bioService.isBiometricEnabled();
      
      // If biometric login is not enabled, invalidate the token on the server
      if (!bioEnabled) {
        await _api.post('/auth/logout/', {});
      }
    } catch (_) {}
    _user = null;
    await _api.setToken(null);
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}
