import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/status_badge.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  void _showImagePickerModal(BuildContext context, AuthProvider auth) {
    showModalBottomSheet(
      context: context,
      backgroundColor: context.cardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: context.textSecondary.withAlpha(60),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Change Profile Picture',
                style: TextStyle(
                  color: context.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildPickerOption(
                    context: ctx,
                    icon: Icons.camera_alt_outlined,
                    label: 'Take Photo',
                    color: AppConfig.primaryColor,
                    onTap: () async {
                      Navigator.pop(ctx);
                      await _pickAndUploadImage(context, auth, ImageSource.camera);
                    },
                  ),
                  _buildPickerOption(
                    context: ctx,
                    icon: Icons.photo_library_outlined,
                    label: 'Choose Gallery',
                    color: AppConfig.secondaryColor,
                    onTap: () async {
                      Navigator.pop(ctx);
                      await _pickAndUploadImage(context, auth, ImageSource.gallery);
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPickerOption({
    required BuildContext context,
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: 120,
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: color.withAlpha(30),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withAlpha(80)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(height: 8),
            Text(
              label,
              style: TextStyle(
                color: context.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _pickAndUploadImage(
    BuildContext context,
    AuthProvider auth,
    ImageSource source,
  ) async {
    try {
      final picker = ImagePicker();
      final pickedFile = await picker.pickImage(
        source: source,
        maxWidth: 800,
        maxHeight: 800,
        imageQuality: 85,
      );

      if (pickedFile == null) return;

      final success = await auth.updateProfilePicture(pickedFile.path);

      if (context.mounted) {
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              backgroundColor: AppConfig.accentColor,
              content: Text('Profile picture updated successfully!'),
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              backgroundColor: AppConfig.dangerColor,
              content: Text(auth.errorMessage ?? 'Upload failed.'),
            ),
          );
        }
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppConfig.dangerColor,
            content: Text('Error selecting image: $e'),
          ),
        );
      }
    }
  }

  void _showEditProfileModal(BuildContext context, AuthProvider auth) {
    final user = auth.user;
    final firstNameCtrl = TextEditingController(text: user?.firstName ?? '');
    final lastNameCtrl = TextEditingController(text: user?.lastName ?? '');
    final emailCtrl = TextEditingController(text: user?.email ?? '');
    final phoneCtrl = TextEditingController(text: user?.phone ?? '');
    final designationCtrl = TextEditingController(text: user?.designation ?? '');
    final formKey = GlobalKey<FormState>();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: context.cardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => Padding(
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
                      color: context.textSecondary.withAlpha(60),
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Edit Personal Info',
                  style: TextStyle(
                    color: context.textPrimary,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 20),

                TextFormField(
                  controller: firstNameCtrl,
                  style: TextStyle(color: context.textPrimary),
                  decoration: const InputDecoration(labelText: 'First Name'),
                  validator: (v) => v == null || v.trim().isEmpty ? 'Enter first name' : null,
                ),
                const SizedBox(height: 14),

                TextFormField(
                  controller: lastNameCtrl,
                  style: TextStyle(color: context.textPrimary),
                  decoration: const InputDecoration(labelText: 'Last Name'),
                  validator: (v) => v == null || v.trim().isEmpty ? 'Enter last name' : null,
                ),
                const SizedBox(height: 14),

                TextFormField(
                  controller: emailCtrl,
                  style: TextStyle(color: context.textPrimary),
                  decoration: const InputDecoration(labelText: 'Email Address'),
                  validator: (v) => v == null || v.trim().isEmpty ? 'Enter email address' : null,
                ),
                const SizedBox(height: 14),

                TextFormField(
                  controller: phoneCtrl,
                  style: TextStyle(color: context.textPrimary),
                  decoration: const InputDecoration(labelText: 'Phone Number'),
                ),
                const SizedBox(height: 14),

                TextFormField(
                  controller: designationCtrl,
                  style: TextStyle(color: context.textPrimary),
                  decoration: const InputDecoration(labelText: 'Designation / Job Title'),
                ),
                const SizedBox(height: 24),

                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    onPressed: () async {
                      if (!formKey.currentState!.validate()) return;
                      Navigator.pop(ctx);
                      final ok = await auth.updateProfileInfo(
                        firstName: firstNameCtrl.text.trim(),
                        lastName: lastNameCtrl.text.trim(),
                        email: emailCtrl.text.trim(),
                        phone: phoneCtrl.text.trim(),
                        designation: designationCtrl.text.trim(),
                      );
                      if (context.mounted) {
                        if (ok) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              backgroundColor: AppConfig.accentColor,
                              content: Text('Profile information updated.'),
                            ),
                          );
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              backgroundColor: AppConfig.dangerColor,
                              content: Text(auth.errorMessage ?? 'Update failed.'),
                            ),
                          );
                        }
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppConfig.primaryColor,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    child: const Text('Save Changes', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
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

    final String? avatarUrl = user?.profilePictureUrl;
    final bool hasAvatar = avatarUrl != null && avatarUrl.isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            onPressed: () => _showEditProfileModal(context, auth),
            tooltip: 'Edit Profile Info',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const SizedBox(height: 10),
            GestureDetector(
              onTap: () => _showImagePickerModal(context, auth),
              child: Stack(
                children: [
                  auth.isLoading
                      ? Container(
                          width: 88,
                          height: 88,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: context.surfaceColor,
                          ),
                          child: const Center(
                            child: SpinKitFadingCube(
                              color: AppConfig.primaryColor,
                              size: 28,
                            ),
                          ),
                        )
                      : CircleAvatar(
                          radius: 44,
                          backgroundColor: AppConfig.primaryColor,
                          backgroundImage: hasAvatar ? NetworkImage(avatarUrl) : null,
                          child: !hasAvatar
                              ? Text(
                                  (user?.firstName.isNotEmpty ?? false)
                                      ? user!.firstName[0].toUpperCase()
                                      : 'U',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 36,
                                    fontWeight: FontWeight.bold,
                                  ),
                                )
                              : null,
                        ),
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: AppConfig.primaryColor,
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: context.cardColor,
                          width: 2,
                        ),
                      ),
                      child: const Icon(
                        Icons.camera_alt,
                        color: Colors.white,
                        size: 16,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            Text(
              user?.fullName ?? 'Staff Member',
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              user?.email ?? '',
              style: const TextStyle(color: AppConfig.secondaryColor, fontSize: 14),
            ),
            const SizedBox(height: 10),
            StatusBadge(status: user?.role ?? 'STAFF', displayLabel: user?.role),
            const SizedBox(height: 24),

            // Edit Profile Info Button
            OutlinedButton.icon(
              onPressed: () => _showEditProfileModal(context, auth),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppConfig.primaryColor),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.edit_note_outlined, color: AppConfig.primaryColor),
              label: const Text('Edit Personal Info', style: TextStyle(color: AppConfig.primaryColor, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 20),

            CustomCard(
              child: Column(
                children: [
                  _buildProfileRow(Icons.badge_outlined, 'Staff ID', user?.staffId ?? 'N/A'),
                  const Divider(height: 16),
                  _buildProfileRow(Icons.work_outline, 'Designation', user?.designation ?? 'N/A'),
                  const Divider(height: 16),
                  _buildProfileRow(Icons.business_outlined, 'Department', user?.departmentName ?? 'N/A'),
                  const Divider(height: 16),
                  _buildProfileRow(Icons.supervisor_account_outlined, 'Supervisor', user?.supervisorName ?? 'None Assigned'),
                  const Divider(height: 16),
                  _buildProfileRow(Icons.phone_outlined, 'Phone', user?.phone.isNotEmpty == true ? user!.phone : 'N/A'),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Change Password Card
            CustomCard(
              onTap: () => _showChangePasswordModal(context, auth),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppConfig.primaryColor.withAlpha(30),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.lock_reset, color: AppConfig.primaryColor),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Change Password', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
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
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppConfig.secondaryColor, size: 20),
          const SizedBox(width: 14),
          Text(label, style: const TextStyle(fontSize: 14)),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              value, 
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              textAlign: TextAlign.right,
              softWrap: true,
            ),
          ),
        ],
      ),
    );
  }
}
