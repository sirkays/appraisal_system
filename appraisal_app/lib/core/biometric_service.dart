import 'package:local_auth/local_auth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class BiometricService {
  static final BiometricService _instance = BiometricService._internal();
  factory BiometricService() => _instance;
  BiometricService._internal();

  final LocalAuthentication _localAuth = LocalAuthentication();
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  static const String _keyBiometricEnabled = 'biometric_enabled';
  static const String _keySavedToken = 'biometric_saved_token';

  Future<bool> isBiometricAvailable() async {
    try {
      final bool canAuthenticateWithBiometrics = await _localAuth.canCheckBiometrics;
      final bool canAuthenticate =
          canAuthenticateWithBiometrics || await _localAuth.isDeviceSupported();
      return canAuthenticate;
    } catch (e) {
      return false;
    }
  }

  Future<bool> authenticate() async {
    try {
      return await _localAuth.authenticate(
        localizedReason: 'Please authenticate to log in',
        biometricOnly: false,
      );
    } catch (e) {
      return false;
    }
  }

  Future<bool> isBiometricEnabled() async {
    final value = await _secureStorage.read(key: _keyBiometricEnabled);
    return value == 'true';
  }

  Future<void> setBiometricEnabled(bool isEnabled) async {
    await _secureStorage.write(
      key: _keyBiometricEnabled,
      value: isEnabled ? 'true' : 'false',
    );
    if (!isEnabled) {
      await clearSavedToken();
    }
  }

  Future<String?> getSavedToken() async {
    return await _secureStorage.read(key: _keySavedToken);
  }

  Future<void> saveToken(String token) async {
    await _secureStorage.write(key: _keySavedToken, value: token);
  }

  Future<void> clearSavedToken() async {
    await _secureStorage.delete(key: _keySavedToken);
  }
}
