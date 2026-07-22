import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../core/api_service.dart';
import '../../core/biometric_service.dart';
import '../../providers/auth_provider.dart';
import '../../providers/theme_provider.dart';
import '../../widgets/custom_card.dart';

class BiometricSettingsCard extends StatefulWidget {
  const BiometricSettingsCard({super.key});

  @override
  State<BiometricSettingsCard> createState() => _BiometricSettingsCardState();
}

class _BiometricSettingsCardState extends State<BiometricSettingsCard> {
  bool _isEnabled = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadStatus();
  }

  Future<void> _loadStatus() async {
    final enabled = await BiometricService().isBiometricEnabled();
    if (mounted) {
      setState(() {
        _isEnabled = enabled;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const SizedBox.shrink();

    return CustomCard(
      child: Row(
        children: [
          const Icon(Icons.fingerprint, color: AppConfig.primaryColor),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Biometric Login', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                Text(
                  _isEnabled ? 'Biometric login is enabled' : 'Biometric login is disabled',
                  style: TextStyle(fontSize: 12, color: context.textSecondary),
                ),
              ],
            ),
          ),
          Switch.adaptive(
            value: _isEnabled,
            activeColor: AppConfig.primaryColor,
            onChanged: (val) async {
              final bioService = BiometricService();
              
              if (val) {
                // If enabling, authenticate first
                final authenticated = await bioService.authenticate();
                if (!authenticated) return;
                
                // Get current token from ApiService to save it
                final token = await ApiService().token;
                if (token != null && token.isNotEmpty) {
                    await bioService.setBiometricEnabled(true);
                    await bioService.saveToken(token);
                    setState(() => _isEnabled = true);
                } else {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Cannot enable biometrics: No active session.')),
                      );
                    }
                }
              } else {
                // Disabling
                await bioService.setBiometricEnabled(false);
                setState(() => _isEnabled = false);
              }
            },
          ),
        ],
      ),
    );
  }
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  void _showServerConfigDialog(BuildContext context) {
    final apiService = ApiService();
    final urlController = TextEditingController();

    apiService.baseUrl.then((url) {
      urlController.text = url;
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: context.cardColor,
          title: Text('Backend API Base URL', style: TextStyle(color: context.textPrimary)),
          content: TextField(
            controller: urlController,
            style: TextStyle(color: context.textPrimary),
            decoration: InputDecoration(
              hintText: 'http://127.0.0.1:9092/api',
              hintStyle: TextStyle(color: context.textSecondary),
              labelText: 'Django API URL',
              labelStyle: const TextStyle(color: AppConfig.secondaryColor),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text('Cancel', style: TextStyle(color: context.textSecondary)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppConfig.primaryColor),
              onPressed: () async {
                await apiService.setBaseUrl(urlController.text.trim());
                if (context.mounted) {
                  Navigator.pop(ctx);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('API Base URL updated.')),
                  );
                }
              },
              child: const Text('Save', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      );
    });
  }

  void _showChangePasswordModal(BuildContext parentContext, AuthProvider auth) {
    final currentPasswordCtrl = TextEditingController();
    final newPasswordCtrl = TextEditingController();
    final confirmPasswordCtrl = TextEditingController();
    bool obscureCurrent = true;
    bool obscureNew = true;
    bool obscureConfirm = true;
    bool isSubmitting = false;
    String? modalError;
    final formKey = GlobalKey<FormState>();

    showModalBottomSheet(
      context: parentContext,
      isScrollControlled: true,
      backgroundColor: parentContext.cardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (modalContext, setModalState) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom,
            top: 24,
            left: 20,
            right: 20,
          ),
          child: SingleChildScrollView(
            child: Form(
              key: formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                        color: parentContext.textSecondary.withAlpha(60),
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      const Icon(Icons.lock_reset, color: AppConfig.primaryColor, size: 28),
                      const SizedBox(width: 12),
                      Text(
                        'Change Password',
                        style: TextStyle(
                          color: parentContext.textPrimary,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  if (modalError != null) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppConfig.dangerColor.withAlpha(30),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppConfig.dangerColor.withAlpha(80)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline, color: AppConfig.dangerColor, size: 20),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              modalError!,
                              style: const TextStyle(color: AppConfig.dangerColor, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Current Password
                  TextFormField(
                    controller: currentPasswordCtrl,
                    obscureText: obscureCurrent,
                    style: TextStyle(color: parentContext.textPrimary),
                    decoration: InputDecoration(
                      labelText: 'Current Password',
                      prefixIcon: const Icon(Icons.lock_outline, color: AppConfig.primaryColor),
                      suffixIcon: IconButton(
                        icon: Icon(
                          obscureCurrent ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                          color: parentContext.textSecondary,
                        ),
                        onPressed: () => setModalState(() => obscureCurrent = !obscureCurrent),
                      ),
                    ),
                    validator: (v) => v == null || v.isEmpty ? 'Enter current password' : null,
                  ),
                  const SizedBox(height: 14),

                  // New Password
                  TextFormField(
                    controller: newPasswordCtrl,
                    obscureText: obscureNew,
                    style: TextStyle(color: parentContext.textPrimary),
                    decoration: InputDecoration(
                      labelText: 'New Password',
                      prefixIcon: const Icon(Icons.key_outlined, color: AppConfig.primaryColor),
                      suffixIcon: IconButton(
                        icon: Icon(
                          obscureNew ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                          color: parentContext.textSecondary,
                        ),
                        onPressed: () => setModalState(() => obscureNew = !obscureNew),
                      ),
                    ),
                    validator: (v) {
                      if (v == null || v.isEmpty) return 'Enter new password';
                      if (v.length < 8) return 'Password must be at least 8 characters';
                      return null;
                    },
                  ),
                  const SizedBox(height: 14),

                  // Confirm Password
                  TextFormField(
                    controller: confirmPasswordCtrl,
                    obscureText: obscureConfirm,
                    style: TextStyle(color: parentContext.textPrimary),
                    decoration: InputDecoration(
                      labelText: 'Confirm New Password',
                      prefixIcon: const Icon(Icons.check_circle_outline, color: AppConfig.primaryColor),
                      suffixIcon: IconButton(
                        icon: Icon(
                          obscureConfirm ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                          color: parentContext.textSecondary,
                        ),
                        onPressed: () => setModalState(() => obscureConfirm = !obscureConfirm),
                      ),
                    ),
                    validator: (v) {
                      if (v == null || v.isEmpty) return 'Confirm your new password';
                      if (v != newPasswordCtrl.text) return 'Passwords do not match';
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),

                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              if (!formKey.currentState!.validate()) return;
                              setModalState(() {
                                isSubmitting = true;
                                modalError = null;
                              });

                              final ok = await auth.changePassword(
                                currentPassword: currentPasswordCtrl.text,
                                newPassword: newPasswordCtrl.text,
                                confirmPassword: confirmPasswordCtrl.text,
                              );

                              if (ok) {
                                Navigator.pop(ctx);
                                ScaffoldMessenger.of(parentContext).showSnackBar(
                                  const SnackBar(
                                    backgroundColor: AppConfig.accentColor,
                                    duration: Duration(seconds: 4),
                                    content: Row(
                                      children: [
                                        Icon(Icons.check_circle, color: Colors.white),
                                        SizedBox(width: 10),
                                        Text('Password changed successfully!', style: TextStyle(fontWeight: FontWeight.bold)),
                                      ],
                                    ),
                                  ),
                                );
                              } else {
                                setModalState(() {
                                  isSubmitting = false;
                                  modalError = auth.errorMessage ?? 'Failed to change password.';
                                });
                              }
                            },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppConfig.primaryColor,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      child: isSubmitting
                          ? const SpinKitThreeBounce(color: Colors.white, size: 20)
                          : const Text('Update Password', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final user = auth.user;
    final themeProvider = Provider.of<ThemeProvider>(context);

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text('Settings'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Profile Overview Tile
            CustomCard(
              onTap: () {
                Navigator.pushNamed(context, '/profile');
              },
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: AppConfig.primaryColor,
                    backgroundImage: (user?.profilePictureUrl != null && user!.profilePictureUrl!.isNotEmpty)
                        ? NetworkImage(user.profilePictureUrl!)
                        : null,
                    child: (user?.profilePictureUrl == null || user!.profilePictureUrl!.isEmpty)
                        ? Text(
                            (user?.firstName.isNotEmpty ?? false) ? user!.firstName[0].toUpperCase() : 'U',
                            style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                          )
                        : null,
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user?.fullName ?? 'Staff Member',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'View & Edit Profile Details',
                          style: TextStyle(fontSize: 12, color: context.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, color: context.textSecondary),
                ],
              ),
            ),
            const SizedBox(height: 20),

            Text(
              'SECURITY & PREFERENCES',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: context.textSecondary,
                letterSpacing: 1,
              ),
            ),
            const SizedBox(height: 10),

            // Change Password Card
            CustomCard(
              onTap: () => _showChangePasswordModal(context, auth),
              child: Row(
                children: [
                  const Icon(Icons.lock_reset, color: AppConfig.primaryColor),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Change Password', style: TextStyle(fontWeight: FontWeight.bold)),
                        const SizedBox(height: 2),
                        Text(
                          'Update your security password',
                          style: TextStyle(fontSize: 12, color: context.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, color: context.textSecondary),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Biometric Settings Card
            const BiometricSettingsCard(),
            const SizedBox(height: 12),

            // Theme Switcher Card
            CustomCard(
              child: Row(
                children: [
                  Icon(
                    themeProvider.isDarkMode ? Icons.dark_mode_outlined : Icons.light_mode_outlined,
                    color: AppConfig.primaryColor,
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Dark Theme Mode', style: TextStyle(fontWeight: FontWeight.bold)),
                        const SizedBox(height: 2),
                        Text(
                          themeProvider.isDarkMode ? 'Currently using Dark Mode' : 'Currently using Light Mode',
                          style: TextStyle(fontSize: 12, color: context.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  Switch.adaptive(
                    value: themeProvider.isDarkMode,
                    activeColor: AppConfig.primaryColor,
                    onChanged: (val) {
                      themeProvider.toggleTheme();
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Backend Settings Card
            CustomCard(
              onTap: () => _showServerConfigDialog(context),
              child: Row(
                children: [
                  const Icon(Icons.dns_outlined, color: AppConfig.secondaryColor),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Backend API Base URL', style: TextStyle(fontWeight: FontWeight.bold)),
                        const SizedBox(height: 2),
                        Text('Configure host address or port', style: TextStyle(fontSize: 12, color: context.textSecondary)),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, color: context.textSecondary),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // Sign Out Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () async {
                  await auth.logout();
                  if (context.mounted) {
                    Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
                  }
                },
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: AppConfig.dangerColor.withAlpha(30),
                  foregroundColor: AppConfig.dangerColor,
                  side: const BorderSide(color: AppConfig.dangerColor),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                icon: const Icon(Icons.logout, color: AppConfig.dangerColor),
                label: const Text('Sign Out', style: TextStyle(color: AppConfig.dangerColor, fontWeight: FontWeight.bold, fontSize: 16)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
