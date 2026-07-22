import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/config.dart';
import '../../models/user_model.dart';
import '../../providers/hr_provider.dart';

class StaffDirectoryScreen extends StatefulWidget {
  const StaffDirectoryScreen({super.key});

  @override
  State<StaffDirectoryScreen> createState() => _StaffDirectoryScreenState();
}

class _StaffDirectoryScreenState extends State<StaffDirectoryScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<HrProvider>(context, listen: false).fetchStaff();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    Provider.of<HrProvider>(context, listen: false).fetchStaff(search: query);
  }

  @override
  Widget build(BuildContext context) {
    final hrProvider = Provider.of<HrProvider>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final staffList = hrProvider.staffList;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Staff Directory',
          style: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w700,
            fontSize: 18,
          ),
        ),
        elevation: 0,
      ),
      body: Column(
        children: [
          // Search Bar
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              onChanged: _onSearchChanged,
              decoration: InputDecoration(
                hintText: 'Search staff by name, ID, email...',
                hintStyle: GoogleFonts.plusJakartaSans(
                  fontSize: 14,
                  color: isDark ? AppConfig.darkTextSecondary : AppConfig.lightTextSecondary,
                ),
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          _onSearchChanged('');
                        },
                      )
                    : null,
                filled: true,
                fillColor: isDark ? AppConfig.darkCardColor : AppConfig.lightCardColor,
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(
                    color: isDark ? Colors.white.withOpacity(0.1) : Colors.black.withOpacity(0.1),
                  ),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(
                    color: isDark ? Colors.white.withOpacity(0.1) : Colors.black.withOpacity(0.1),
                  ),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: AppConfig.primaryColor),
                ),
              ),
            ),
          ),

          // Staff List
          Expanded(
            child: hrProvider.isLoadingStaff
                ? const Center(child: CircularProgressIndicator())
                : staffList.isEmpty
                    ? Center(
                        child: Text(
                          'No staff members found',
                          style: GoogleFonts.plusJakartaSans(
                            color: isDark ? AppConfig.darkTextSecondary : AppConfig.lightTextSecondary,
                          ),
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: () => hrProvider.fetchStaff(search: _searchController.text),
                        child: ListView.separated(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          itemCount: staffList.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (context, index) {
                            final staff = staffList[index];
                            return _buildStaffCard(context, staff, isDark);
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildStaffCard(BuildContext context, UserModel staff, bool isDark) {
    return Container(
      decoration: BoxDecoration(
        color: isDark ? AppConfig.darkCardColor : AppConfig.lightCardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark ? Colors.white.withOpacity(0.08) : Colors.black.withOpacity(0.06),
        ),
      ),
      child: ListTile(
        onTap: () => _showStaffDetailsModal(context, staff, isDark),
        contentPadding: const EdgeInsets.all(12),
        leading: CircleAvatar(
          radius: 24,
          backgroundColor: AppConfig.primaryColor.withOpacity(0.15),
          backgroundImage: staff.profilePictureUrl != null && staff.profilePictureUrl!.isNotEmpty
              ? NetworkImage(staff.profilePictureUrl!)
              : null,
          child: staff.profilePictureUrl == null || staff.profilePictureUrl!.isEmpty
              ? Text(
                  staff.firstName.isNotEmpty ? staff.firstName[0].toUpperCase() : 'U',
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.bold,
                    color: AppConfig.primaryColor,
                  ),
                )
              : null,
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                staff.fullName,
                style: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
            ),
            _buildRoleBadge(staff.role),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'ID: ${staff.staffId} • ${staff.designation.isNotEmpty ? staff.designation : "Staff"}',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  color: isDark ? AppConfig.darkTextSecondary : AppConfig.lightTextSecondary,
                ),
              ),
              if (staff.departmentName != null)
                Text(
                  'Dept: ${staff.departmentName}',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11,
                    color: AppConfig.primaryColor,
                    fontWeight: FontWeight.w500,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRoleBadge(String role) {
    Color color;
    switch (role) {
      case 'HR_ADMIN':
        color = const Color(0xFFEF4444);
        break;
      case 'DIRECTORATE':
        color = const Color(0xFF8B5CF6);
        break;
      case 'HOD':
        color = const Color(0xFF3B82F6);
        break;
      case 'SUPERVISOR':
        color = const Color(0xFFF59E0B);
        break;
      default:
        color = AppConfig.primaryColor;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        role.replaceAll('_', ' '),
        style: GoogleFonts.plusJakartaSans(
          fontSize: 10,
          fontWeight: FontWeight.bold,
          color: color,
        ),
      ),
    );
  }

  void _showStaffDetailsModal(BuildContext context, UserModel staff, bool isDark) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: isDark ? AppConfig.darkCardColor : AppConfig.lightCardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: isDark ? Colors.white24 : Colors.black12,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 20),
              CircleAvatar(
                radius: 36,
                backgroundColor: AppConfig.primaryColor.withOpacity(0.15),
                backgroundImage: staff.profilePictureUrl != null && staff.profilePictureUrl!.isNotEmpty
                    ? NetworkImage(staff.profilePictureUrl!)
                    : null,
                child: staff.profilePictureUrl == null || staff.profilePictureUrl!.isEmpty
                    ? Text(
                        staff.firstName.isNotEmpty ? staff.firstName[0].toUpperCase() : 'U',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: AppConfig.primaryColor,
                        ),
                      )
                    : null,
              ),
              const SizedBox(height: 12),
              Text(
                staff.fullName,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              _buildRoleBadge(staff.role),
              const SizedBox(height: 20),
              const Divider(),
              _buildDetailRow('Staff ID', staff.staffId, isDark),
              _buildDetailRow('Email', staff.email, isDark),
              _buildDetailRow('Phone', staff.phone.isNotEmpty ? staff.phone : 'N/A', isDark),
              _buildDetailRow('Designation', staff.designation.isNotEmpty ? staff.designation : 'N/A', isDark),
              _buildDetailRow('Department', staff.departmentName ?? 'N/A', isDark),
              _buildDetailRow('Supervisor', staff.supervisorName ?? 'N/A', isDark),
              const SizedBox(height: 16),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDetailRow(String label, String value, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              color: isDark ? AppConfig.darkTextSecondary : AppConfig.lightTextSecondary,
            ),
          ),
          Text(
            value,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
