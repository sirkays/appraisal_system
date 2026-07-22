import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/config.dart';
import '../../core/api_service.dart';
import '../../providers/auth_provider.dart';
import '../../core/biometric_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  bool _canUseBiometrics = false;
  bool _isCheckingBiometrics = true;

  @override
  void initState() {
    super.initState();
    _checkBiometrics();
  }

  Future<void> _checkBiometrics() async {
    final bioService = BiometricService();
    final enabled = await bioService.isBiometricEnabled();
    final token = await bioService.getSavedToken();
    if (!mounted) return;
    
    if (enabled && token != null && token.isNotEmpty) {
      setState(() {
        _canUseBiometrics = true;
      });
    }
    setState(() {
      _isCheckingBiometrics = false;
    });
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
  void _showServerConfigDialog() {
    final apiService = ApiService();
    final urlController = TextEditingController();

    apiService.baseUrl.then((url) {
      urlController.text = url;
      if (!mounted) return;
      showDialog(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setDialogState) => AlertDialog(
            backgroundColor: context.cardColor,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                Icon(Icons.wifi_tethering, color: AppConfig.primaryColor, size: 22),
                const SizedBox(width: 8),
                Text('Server Connection', style: TextStyle(color: context.textPrimary, fontSize: 17, fontWeight: FontWeight.bold)),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppConfig.primaryColor.withAlpha(20),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppConfig.primaryColor.withAlpha(40)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('📱 USB (adb reverse):', style: TextStyle(color: context.textPrimary, fontSize: 11, fontWeight: FontWeight.bold)),
                      Text('http://127.0.0.1:9092/api', style: TextStyle(color: context.textSecondary, fontSize: 11, fontFamily: 'monospace')),
                      const SizedBox(height: 6),
                      Text('📶 Wi-Fi (same network):', style: TextStyle(color: context.textPrimary, fontSize: 11, fontWeight: FontWeight.bold)),
                      Text('Use your computer\'s IP:9092/api', style: TextStyle(color: context.textSecondary, fontSize: 11)),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: urlController,
                  style: TextStyle(color: context.textPrimary, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'http://192.168.x.x:9092/api',
                    hintStyle: TextStyle(color: context.textSecondary),
                    labelText: 'API Base URL',
                    labelStyle: const TextStyle(color: AppConfig.secondaryColor),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                    prefixIcon: const Icon(Icons.link, color: AppConfig.primaryColor, size: 18),
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () async {
                  // Reset — clear saved URL so defaultBaseUrl is used
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.remove('api_base_url');
                  apiService.clearBaseUrlCache();
                  if (mounted) {
                    Navigator.pop(ctx);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Reset to default URL.')),
                    );
                  }
                },
                child: Text('Reset', style: TextStyle(color: context.textSecondary)),
              ),
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: Text('Cancel', style: TextStyle(color: context.textSecondary)),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: AppConfig.primaryColor, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                onPressed: () async {
                  await apiService.setBaseUrl(urlController.text.trim());
                  if (mounted) {
                    Navigator.pop(ctx);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Server URL updated.')),
                    );
                  }
                },
                child: const Text('Save', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      );
    });
  }


  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      backgroundColor: context.bgColor,
      body: Stack(
        children: [
          // Background Glows (Emerald and Teal)
          Positioned(
            top: -100,
            left: -100,
            child: Container(
              width: 300,
              height: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppConfig.primaryColor.withAlpha(35),
              ),
            ),
          ),
          Positioned(
            bottom: -80,
            right: -80,
            child: Container(
              width: 280,
              height: 280,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppConfig.secondaryColor.withAlpha(35),
              ),
            ),
          ),

          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 28),
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 440),
                  padding: const EdgeInsets.all(32),
                  decoration: BoxDecoration(
                    color: context.cardColor,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: context.textSecondary.withAlpha(35)),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withAlpha(context.isDarkMode ? 80 : 20),
                        blurRadius: 24,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            GestureDetector(
                              onLongPress: _showServerConfigDialog,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                decoration: BoxDecoration(
                                  gradient: AppConfig.primaryGradient,
                                  borderRadius: BorderRadius.circular(14),
                                  boxShadow: [
                                    BoxShadow(
                                      color: AppConfig.primaryColor.withAlpha(80),
                                      blurRadius: 10,
                                      offset: const Offset(0, 4),
                                    ),
                                  ],
                                ),
                                child: const Text(
                                  'SAP',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w900,
                                    fontSize: 16,
                                    letterSpacing: 1.5,
                                  ),
                                ),
                              ),
                            ),
                            IconButton(
                              icon: Icon(Icons.settings_outlined, color: context.textSecondary),
                              tooltip: 'Configure Server URL',
                              onPressed: _showServerConfigDialog,
                            ),
                          ],
                        ),
                        const SizedBox(height: 24),

                        Text(
                          'Welcome Back',
                          style: TextStyle(
                            color: context.textPrimary,
                            fontSize: 26,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Staff Performance Appraisal System',
                          style: TextStyle(color: context.textSecondary, fontSize: 14),
                        ),
                        const SizedBox(height: 28),

                        if (authProvider.errorMessage != null) ...[
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppConfig.dangerColor.withAlpha(35),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppConfig.dangerColor.withAlpha(100)),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.error_outline, color: AppConfig.dangerColor, size: 20),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    authProvider.errorMessage!,
                                    style: const TextStyle(color: AppConfig.dangerColor, fontSize: 13),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 20),
                        ],

                        // Username Input
                        TextFormField(
                          controller: _usernameController,
                          style: TextStyle(color: context.textPrimary),
                          decoration: InputDecoration(
                            labelText: 'Username or Staff ID',
                            labelStyle: TextStyle(color: context.textSecondary),
                            prefixIcon: const Icon(Icons.person_outline, color: AppConfig.primaryColor),
                            filled: true,
                            fillColor: context.surfaceColor.withAlpha(100),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: BorderSide(color: context.textSecondary.withAlpha(30)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: BorderSide(color: context.textSecondary.withAlpha(30)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: const BorderSide(color: AppConfig.primaryColor, width: 2),
                            ),
                          ),
                          validator: (val) {
                            if (val == null || val.trim().isEmpty) {
                              return 'Please enter your username';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 18),

                        // Password Input
                        TextFormField(
                          controller: _passwordController,
                          obscureText: _obscurePassword,
                          style: TextStyle(color: context.textPrimary),
                          decoration: InputDecoration(
                            labelText: 'Password',
                            labelStyle: TextStyle(color: context.textSecondary),
                            prefixIcon: const Icon(Icons.lock_outline, color: AppConfig.primaryColor),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                                color: context.textSecondary,
                              ),
                              onPressed: () {
                                setState(() {
                                  _obscurePassword = !_obscurePassword;
                                });
                              },
                            ),
                            filled: true,
                            fillColor: context.surfaceColor.withAlpha(100),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: BorderSide(color: context.textSecondary.withAlpha(30)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: BorderSide(color: context.textSecondary.withAlpha(30)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: const BorderSide(color: AppConfig.primaryColor, width: 2),
                            ),
                          ),
                          validator: (val) {
                            if (val == null || val.isEmpty) {
                              return 'Please enter your password';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 28),

                        // Submit Button
                        SizedBox(
                          height: 52,
                          child: ElevatedButton(
                            onPressed: authProvider.isLoading
                                ? null
                                : () async {
                                    if (_formKey.currentState!.validate()) {
                                      final success = await authProvider.login(
                                        _usernameController.text.trim(),
                                        _passwordController.text,
                                      );
                                      if (mounted && success) {
                                        Navigator.pushReplacementNamed(context, '/main');
                                      }
                                    }
                                  },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppConfig.primaryColor,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                              elevation: 4,
                            ),
                            child: authProvider.isLoading
                                ? const SpinKitThreeBounce(color: Colors.white, size: 22)
                                : const Text(
                                    'Sign In',
                                    style: TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                          ),
                        ),
                        if (_canUseBiometrics && !_isCheckingBiometrics) ...[
                          const SizedBox(height: 20),
                          Center(
                            child: IconButton(
                              icon: const Icon(Icons.fingerprint, size: 48, color: AppConfig.primaryColor),
                              onPressed: authProvider.isLoading
                                  ? null
                                  : () async {
                                      final success = await authProvider.loginWithBiometrics();
                                      if (mounted && success) {
                                        Navigator.pushReplacementNamed(context, '/main');
                                      }
                                    },
                              tooltip: 'Login with Biometrics',
                            ),
                          ),
                          const Center(
                            child: Text(
                              'Use Biometrics',
                              style: TextStyle(color: AppConfig.primaryColor, fontSize: 13, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
