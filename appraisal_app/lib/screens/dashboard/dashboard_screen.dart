import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../providers/auth_provider.dart';
import '../../providers/appraisal_provider.dart';
import '../../providers/reviewer_provider.dart';
import '../../providers/notification_provider.dart';
import '../../providers/theme_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/metric_tile.dart';
import '../../widgets/status_badge.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadData();
    });
  }

  Future<void> _loadData() async {
    if (!mounted) return;
    final appraisalProvider =
        Provider.of<AppraisalProvider>(context, listen: false);
    final notificationProvider =
        Provider.of<NotificationProvider>(context, listen: false);
    final reviewerProvider =
        Provider.of<ReviewerProvider>(context, listen: false);

    await appraisalProvider.fetchDashboard();
    await appraisalProvider.fetchEligibleCycles();
    await notificationProvider.fetchNotifications();

    if (!mounted) return;
    final auth = Provider.of<AuthProvider>(context, listen: false);
    if (auth.user?.isReviewer ?? false) {
      await reviewerProvider.fetchQueue();
    }
  }

  Future<void> _handleStartAppraisal({int? cycleId}) async {
    final appraisalProvider =
        Provider.of<AppraisalProvider>(context, listen: false);
    final appraisalId =
        await appraisalProvider.startAppraisal(cycleId: cycleId);
    if (!mounted) return;

    if (appraisalId != null) {
      await Navigator.pushNamed(
        context,
        '/self_appraisal',
        arguments: appraisalId,
      );
      // Refresh dashboard after returning
      if (mounted) _loadData();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: AppConfig.dangerColor,
          content: Text(
              appraisalProvider.errorMessage ?? 'Could not start appraisal.'),
        ),
      );
    }
  }

  void _showCycleSwitcher(BuildContext context) {
    final appraisalProvider =
        Provider.of<AppraisalProvider>(context, listen: false);
    final cycles = appraisalProvider.eligibleCycles;
    if (cycles.isEmpty) return;

    showModalBottomSheet(
      context: context,
      backgroundColor: context.cardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
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
                'Switch Appraisal Cycle',
                style: TextStyle(
                  color: context.textPrimary,
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Select a cycle to view its dashboard',
                style: TextStyle(color: context.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: 16),
              ...cycles.map((cycle) {
                final isSelected =
                    cycle.id == appraisalProvider.selectedCycleId;
                return ListTile(
                  leading: CircleAvatar(
                    radius: 10,
                    backgroundColor: isSelected
                        ? AppConfig.accentColor
                        : context.textSecondary.withAlpha(40),
                  ),
                  title: Text(
                    cycle.name,
                    style: TextStyle(
                      color: context.textPrimary,
                      fontWeight: isSelected
                          ? FontWeight.bold
                          : FontWeight.normal,
                    ),
                  ),
                  subtitle: Text(
                    '${cycle.startDate} — ${cycle.endDate}',
                    style:
                        TextStyle(color: context.textSecondary, fontSize: 12),
                  ),
                  trailing: isSelected
                      ? const Icon(Icons.check_circle,
                          color: AppConfig.accentColor)
                      : null,
                  onTap: () {
                    Navigator.pop(ctx);
                    Provider.of<AppraisalProvider>(context, listen: false)
                        .switchCycle(cycle.id);
                  },
                );
              }),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final user = auth.user;
    final appraisalProvider = Provider.of<AppraisalProvider>(context);
    final notifProvider = Provider.of<NotificationProvider>(context);

    final dashData = appraisalProvider.dashboardData;
    final activeCycleJson = dashData?['active_cycle'];
    final myAppraisalJson = dashData?['my_active_appraisal'];
    final pendingCount = dashData?['pending_reviews_count'] ?? 0;
    final completedCount = dashData?['my_completed_count'] ?? 0;

    final eligibleCycles = appraisalProvider.eligibleCycles;
    final hasMultipleCycles = eligibleCycles.length > 1;

    // Derive appraisal state helpers
    final String? appraisalStatus = myAppraisalJson?['status'];
    final bool canStartOrContinue = activeCycleJson != null &&
        (myAppraisalJson == null ||
            ['NOT_STARTED', 'DRAFT', 'RETURNED_TO_STAFF']
                .contains(appraisalStatus));
    final bool isReturned = appraisalStatus == 'RETURNED_TO_STAFF';
    final int? appraisalId = myAppraisalJson?['id'];

    // Completion progress (rough % from step number)
    double progress = 0;
    if (myAppraisalJson != null) {
      if (['APPROVED', 'STAFF_ACKNOWLEDGED'].contains(appraisalStatus)) {
        progress = 1.0;
      } else if (appraisalStatus == 'SUBMITTED' ||
          appraisalStatus == 'AWAITING_STEP_REVIEW') {
        final step = (myAppraisalJson['current_step_number'] as num?)?.toInt() ?? 0;
        progress = 0.3 + (step * 0.15).clamp(0.0, 0.65);
      } else if (appraisalStatus == 'DRAFT') {
        progress = 0.1;
      }
    }

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        elevation: 0,
        title: Text(
          user?.fullName ?? AppConfig.appName,
          style:
              const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        actions: [
          // Cycle switcher icon (only when multiple eligible cycles)
          if (hasMultipleCycles)
            IconButton(
              icon: const Icon(Icons.swap_horiz_rounded),
              tooltip: 'Switch Cycle',
              onPressed: () => _showCycleSwitcher(context),
            ),
          Consumer<ThemeProvider>(
            builder: (context, themeProvider, _) {
              return IconButton(
                icon: Icon(
                  themeProvider.isDarkMode
                      ? Icons.wb_sunny_outlined
                      : Icons.nightlight_round,
                ),
                onPressed: themeProvider.toggleTheme,
                tooltip: themeProvider.isDarkMode
                    ? 'Switch to Light Theme'
                    : 'Switch to Dark Theme',
              );
            },
          ),
          Stack(
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_outlined),
                onPressed: () =>
                    Navigator.pushNamed(context, '/notifications'),
              ),
              if (notifProvider.unreadCount > 0)
                Positioned(
                  right: 8,
                  top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: AppConfig.dangerColor,
                      shape: BoxShape.circle,
                    ),
                    child: Text(
                      '${notifProvider.unreadCount}',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.person_outline),
            onPressed: () => Navigator.pushNamed(context, '/profile'),
          ),
        ],
      ),
      body: appraisalProvider.isLoading
          ? const Center(
              child: SpinKitFadingCube(
                  color: AppConfig.primaryColor, size: 40))
          : RefreshIndicator(
              onRefresh: _loadData,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // ── User profile card ──────────────────────────────
                    CustomCard(
                      onTap: () {
                        Navigator.pushNamed(context, '/profile');
                      },
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 28,
                            backgroundColor: AppConfig.primaryColor,
                            backgroundImage: (user?.profilePictureUrl != null && user!.profilePictureUrl!.isNotEmpty)
                                ? NetworkImage(user.profilePictureUrl!)
                                : null,
                            child: (user?.profilePictureUrl == null || user!.profilePictureUrl!.isEmpty)
                                ? Text(
                                    (user?.firstName.isNotEmpty ?? false)
                                        ? user!.firstName[0].toUpperCase()
                                        : 'U',
                                    style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 24,
                                        fontWeight: FontWeight.bold),
                                  )
                                : null,
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  user?.fullName ?? '',
                                  style: TextStyle(
                                    color: context.textPrimary,
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${user?.designation ?? ''} • ${user?.departmentName ?? ''}',
                                  style: TextStyle(
                                      color: context.textSecondary,
                                      fontSize: 13),
                                ),
                                const SizedBox(height: 6),
                                StatusBadge(
                                    status: user?.role ?? 'STAFF',
                                    displayLabel: user?.role),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),

                    // ── Return-to-staff banner ─────────────────────────
                    if (isReturned) ...[
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: AppConfig.warningColor.withAlpha(30),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                              color: AppConfig.warningColor.withAlpha(120)),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.info_outline,
                                color: AppConfig.warningColor, size: 20),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Appraisal Returned for Revision',
                                    style: TextStyle(
                                      color: AppConfig.warningColor,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 14,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    (myAppraisalJson?['return_notes'] != null && (myAppraisalJson!['return_notes'] as String).isNotEmpty)
                                        ? 'Reason: ${myAppraisalJson!['return_notes']}'
                                        : (myAppraisalJson?['supervisor_return_notes'] != null && (myAppraisalJson!['supervisor_return_notes'] as String).isNotEmpty)
                                            ? 'Reason: ${myAppraisalJson!['supervisor_return_notes']}'
                                            : 'Your reviewer has returned your appraisal. Please revise and resubmit.',
                                    style: TextStyle(
                                        color: context.textSecondary,
                                        fontSize: 13),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],

                    // ── Active cycle card ──────────────────────────────
                    if (activeCycleJson != null) ...[
                      CustomCard(
                        color: context.surfaceColor.withAlpha(100),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment:
                                  MainAxisAlignment.spaceBetween,
                              children: [
                                const Text(
                                  'ACTIVE APPRAISAL CYCLE',
                                  style: TextStyle(
                                    color: AppConfig.secondaryColor,
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    letterSpacing: 1,
                                  ),
                                ),
                                StatusBadge(
                                    status: activeCycleJson['status'] ?? ''),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              activeCycleJson['name'] ?? 'Annual Review',
                              style: TextStyle(
                                color: context.textPrimary,
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              '${activeCycleJson['start_date']} — ${activeCycleJson['end_date']}',
                              style: TextStyle(
                                  color: context.textSecondary, fontSize: 13),
                            ),

                            // Progress bar
                            if (myAppraisalJson != null) ...[
                              const SizedBox(height: 14),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    myAppraisalJson['status_display'] ??
                                        appraisalStatus ??
                                        '',
                                    style: TextStyle(
                                        color: context.textSecondary,
                                        fontSize: 12),
                                  ),
                                  Text(
                                    '${(progress * 100).toInt()}%',
                                    style: const TextStyle(
                                        color: AppConfig.accentColor,
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(6),
                                child: LinearProgressIndicator(
                                  value: progress,
                                  minHeight: 8,
                                  backgroundColor:
                                      context.textSecondary.withAlpha(30),
                                  valueColor:
                                      const AlwaysStoppedAnimation<Color>(
                                          AppConfig.accentColor),
                                ),
                              ),
                            ],

                            // Start / Continue button
                            if (canStartOrContinue) ...[
                              const SizedBox(height: 16),
                              SizedBox(
                                width: double.infinity,
                                child: appraisalProvider.isStarting
                                    ? const Center(
                                        child: SpinKitFadingCube(
                                            color: AppConfig.primaryColor,
                                            size: 28))
                                    : ElevatedButton.icon(
                                        onPressed: () => _handleStartAppraisal(
                                          cycleId: activeCycleJson['id'],
                                        ),
                                        icon: Icon(
                                          isReturned
                                              ? Icons.edit_outlined
                                              : myAppraisalJson != null
                                                  ? Icons.arrow_forward
                                                  : Icons.play_arrow_rounded,
                                        ),
                                        label: Text(
                                          isReturned
                                              ? 'Revise & Resubmit'
                                              : myAppraisalJson != null
                                                  ? 'Continue Self-Appraisal'
                                                  : 'Start Self-Appraisal',
                                          style: const TextStyle(
                                              fontWeight: FontWeight.bold),
                                        ),
                                        style: ElevatedButton.styleFrom(
                                          padding: const EdgeInsets.symmetric(
                                              vertical: 14),
                                          backgroundColor:
                                              AppConfig.primaryColor,
                                          foregroundColor: Colors.white,
                                          shape: RoundedRectangleBorder(
                                            borderRadius:
                                                BorderRadius.circular(12),
                                          ),
                                        ),
                                      ),
                              ),
                            ],

                            // View details button (submitted / approved etc.)
                            if (!canStartOrContinue && appraisalId != null) ...[
                              const SizedBox(height: 16),
                              SizedBox(
                                width: double.infinity,
                                child: OutlinedButton.icon(
                                  onPressed: () async {
                                    await Navigator.pushNamed(
                                      context,
                                      '/appraisal_detail',
                                      arguments: appraisalId,
                                    );
                                    if (mounted) _loadData();
                                  },
                                  icon: const Icon(Icons.visibility_outlined),
                                  label: const Text('View Appraisal Details'),
                                  style: OutlinedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(
                                        vertical: 14),
                                    side: const BorderSide(
                                        color: AppConfig.primaryColor),
                                    foregroundColor: AppConfig.primaryColor,
                                    shape: RoundedRectangleBorder(
                                      borderRadius:
                                          BorderRadius.circular(12),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                    ] else ...[
                      // No active cycle for this user
                      CustomCard(
                        color: context.surfaceColor.withAlpha(60),
                        child: Column(
                          children: [
                            Icon(Icons.event_busy_outlined,
                                size: 40,
                                color: context.textSecondary.withAlpha(120)),
                            const SizedBox(height: 8),
                            Text(
                              'No Active Appraisal Cycle',
                              style: TextStyle(
                                  color: context.textPrimary,
                                  fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'There is currently no active cycle assigned to you.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                  color: context.textSecondary, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                    ],

                    // ── Metric tiles ───────────────────────────────────
                    Row(
                      children: [
                        Expanded(
                          child: MetricTile(
                            title: 'Completed',
                            value: '$completedCount',
                            icon: Icons.check_circle_outline,
                            color: AppConfig.accentColor,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: MetricTile(
                            title: 'Pending Reviews',
                            value: '$pendingCount',
                            icon: Icons.rate_review_outlined,
                            color: AppConfig.secondaryColor,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
