import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/config.dart';
import '../../providers/hr_provider.dart';
import 'staff_directory_screen.dart';
import 'departments_screen.dart';
import 'branches_screen.dart';
import 'reports_analytics_screen.dart';

class HrDashboardScreen extends StatefulWidget {
  const HrDashboardScreen({super.key});

  @override
  State<HrDashboardScreen> createState() => _HrDashboardScreenState();
}

class _HrDashboardScreenState extends State<HrDashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<HrProvider>(context, listen: false).fetchHrDashboard();
    });
  }

  @override
  Widget build(BuildContext context) {
    final hrProvider = Provider.of<HrProvider>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final data = hrProvider.dashboardData;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'HR Administration',
          style: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w700,
            fontSize: 20,
          ),
        ),
        elevation: 0,
        backgroundColor: Colors.transparent,
      ),
      body: hrProvider.isLoadingDashboard
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () => hrProvider.fetchHrDashboard(),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16.0),
                physics: const AlwaysScrollableScrollPhysics(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header greeting
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        gradient: AppConfig.primaryGradient,
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                            color: AppConfig.primaryColor.withOpacity(0.3),
                            blurRadius: 15,
                            offset: const Offset(0, 5),
                          ),
                        ],
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.2),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.admin_panel_settings_outlined,
                              color: Colors.white,
                              size: 32,
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'HR Management Hub',
                                  style: GoogleFonts.plusJakartaSans(
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Appraisals, Staff Directory & Analytics',
                                  style: GoogleFonts.plusJakartaSans(
                                    fontSize: 13,
                                    color: Colors.white.withOpacity(0.9),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Key Overview Cards Grid
                    Text(
                      'Overview Metrics',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    GridView.count(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      shrinkWrap: true,
                      childAspectRatio: 1.45,
                      physics: const NeverScrollableScrollPhysics(),
                      children: [
                        _buildMetricCard(
                          context,
                          title: 'Total Staff',
                          value: '${data?['total_staff'] ?? 0}',
                          icon: Icons.people_alt_outlined,
                          color: AppConfig.primaryColor,
                          isDark: isDark,
                        ),
                        _buildMetricCard(
                          context,
                          title: 'Active Cycles',
                          value: '${data?['active_cycles_count'] ?? 0}',
                          icon: Icons.calendar_today_outlined,
                          color: AppConfig.secondaryColor,
                          isDark: isDark,
                        ),
                        _buildMetricCard(
                          context,
                          title: 'Completed',
                          value: '${data?['completed_appraisals'] ?? 0}',
                          icon: Icons.task_alt_outlined,
                          color: AppConfig.accentColor,
                          isDark: isDark,
                        ),
                        _buildMetricCard(
                          context,
                          title: 'Pending Reviews',
                          value: '${data?['pending_reviews'] ?? 0}',
                          icon: Icons.pending_actions_outlined,
                          color: AppConfig.warningColor,
                          isDark: isDark,
                        ),
                      ],
                    ),
                    const SizedBox(height: 28),

                    // Quick Management Actions
                    Text(
                      'HR Directory & Reports',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    _buildActionTile(
                      context,
                      title: 'Staff Directory',
                      subtitle: 'Search & view all staff records and roles',
                      icon: Icons.badge_outlined,
                      color: const Color(0xFF3B82F6),
                      isDark: isDark,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const StaffDirectoryScreen()),
                        );
                      },
                    ),
                    const SizedBox(height: 10),
                    _buildActionTile(
                      context,
                      title: 'Departments',
                      subtitle: 'Department listings, HODs, and staff counts',
                      icon: Icons.apartment_outlined,
                      color: const Color(0xFF8B5CF6),
                      isDark: isDark,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const DepartmentsScreen()),
                        );
                      },
                    ),
                    const SizedBox(height: 10),
                    _buildActionTile(
                      context,
                      title: 'Branches',
                      subtitle: 'Company branches and branch staff distribution',
                      icon: Icons.account_tree_outlined,
                      color: const Color(0xFFEC4899),
                      isDark: isDark,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const BranchesScreen()),
                        );
                      },
                    ),
                    const SizedBox(height: 10),
                    _buildActionTile(
                      context,
                      title: 'Reports & Analytics',
                      subtitle: 'Appraisal completion rates and analytics summary',
                      icon: Icons.bar_chart_outlined,
                      color: const Color(0xFF10B981),
                      isDark: isDark,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const ReportsAnalyticsScreen()),
                        );
                      },
                    ),
                    const SizedBox(height: 28),

                    // Department Progress Summary
                    if (data?['department_stats'] != null &&
                        (data!['department_stats'] as List).isNotEmpty) ...[
                      Text(
                        'Department Appraisal Progress',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ListView.separated(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: (data['department_stats'] as List).length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, index) {
                          final dept = data['department_stats'][index];
                          final total = dept['total_appraisals'] ?? 0;
                          final completed = dept['completed_appraisals'] ?? 0;
                          final progress = total > 0 ? (completed / total) : 0.0;

                          return Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: isDark ? AppConfig.darkCardColor : AppConfig.lightCardColor,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: isDark
                                    ? Colors.white.withOpacity(0.08)
                                    : Colors.black.withOpacity(0.06),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      dept['name'] ?? '',
                                      style: GoogleFonts.plusJakartaSans(
                                        fontWeight: FontWeight.w600,
                                        fontSize: 14,
                                      ),
                                    ),
                                    Text(
                                      '$completed / $total Completed',
                                      style: GoogleFonts.plusJakartaSans(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w500,
                                        color: AppConfig.primaryColor,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(4),
                                  child: LinearProgressIndicator(
                                    value: progress.toDouble(),
                                    backgroundColor: isDark
                                        ? AppConfig.darkSurfaceColor
                                        : AppConfig.lightSurfaceColor,
                                    valueColor: const AlwaysStoppedAnimation<Color>(
                                      AppConfig.primaryColor,
                                    ),
                                    minHeight: 6,
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ],
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildMetricCard(
    BuildContext context, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
    required bool isDark,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppConfig.darkCardColor : AppConfig.lightCardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark ? Colors.white.withOpacity(0.08) : Colors.black.withOpacity(0.06),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: isDark ? AppConfig.darkTextSecondary : AppConfig.lightTextSecondary,
                ),
              ),
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: color, size: 18),
              ),
            ],
          ),
          Text(
            value,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionTile(
    BuildContext context, {
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required bool isDark,
    required VoidCallback onTap,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: isDark ? AppConfig.darkCardColor : AppConfig.lightCardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark ? Colors.white.withOpacity(0.08) : Colors.black.withOpacity(0.06),
        ),
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withOpacity(0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: color, size: 24),
        ),
        title: Text(
          title,
          style: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w700,
            fontSize: 15,
          ),
        ),
        subtitle: Text(
          subtitle,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 12,
            color: isDark ? AppConfig.darkTextSecondary : AppConfig.lightTextSecondary,
          ),
        ),
        trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 14),
      ),
    );
  }
}
