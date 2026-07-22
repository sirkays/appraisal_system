import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/config.dart';
import '../providers/auth_provider.dart';
import '../providers/notification_provider.dart';
import '../providers/reviewer_provider.dart';
import 'dashboard/dashboard_screen.dart';
import 'hr/hr_dashboard_screen.dart';
import 'appraisal/my_appraisals_screen.dart';
import 'appraisal/review_queue_screen.dart';
import 'notifications/notifications_screen.dart';
import 'settings/settings_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final user = auth.user;
    final isHrAdmin = user?.isHrAdmin ?? false;
    final isReviewer = user?.isReviewer ?? false;
    final notifProvider = Provider.of<NotificationProvider>(context);
    final reviewerProvider = Provider.of<ReviewerProvider>(context);

    final List<Widget> pages = [
      const DashboardScreen(),
      if (isHrAdmin) const HrDashboardScreen(),
      const MyAppraisalsScreen(),
      if (isReviewer) const ReviewQueueScreen(),
      const NotificationsScreen(),
      const SettingsScreen(),
    ];

    // Ensure index bounds if role or user state changes
    if (_currentIndex >= pages.length) {
      _currentIndex = 0;
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: pages,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: Colors.black.withAlpha(20),
              blurRadius: 10,
            ),
          ],
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) {
            setState(() {
              _currentIndex = index;
            });
          },
          type: BottomNavigationBarType.fixed,
          backgroundColor: isDark ? AppConfig.darkCardColor : AppConfig.lightCardColor,
          selectedItemColor: AppConfig.primaryColor,
          unselectedItemColor: isDark ? AppConfig.darkTextSecondary : AppConfig.lightTextSecondary,
          selectedFontSize: 11,
          unselectedFontSize: 11,
          items: [
            const BottomNavigationBarItem(
              icon: Icon(Icons.dashboard_outlined),
              activeIcon: Icon(Icons.dashboard),
              label: 'Home',
            ),
            if (isHrAdmin)
              const BottomNavigationBarItem(
                icon: Icon(Icons.admin_panel_settings_outlined),
                activeIcon: Icon(Icons.admin_panel_settings),
                label: 'HR Hub',
              ),
            const BottomNavigationBarItem(
              icon: Icon(Icons.assignment_outlined),
              activeIcon: Icon(Icons.assignment),
              label: 'Appraisals',
            ),
            if (isReviewer)
              BottomNavigationBarItem(
                icon: Stack(
                  children: [
                    const Icon(Icons.rate_review_outlined),
                    if (reviewerProvider.queue.isNotEmpty)
                      Positioned(
                        right: 0,
                        top: 0,
                        child: Container(
                          padding: const EdgeInsets.all(2),
                          decoration: const BoxDecoration(
                            color: AppConfig.warningColor,
                            shape: BoxShape.circle,
                          ),
                          constraints: const BoxConstraints(minWidth: 8, minHeight: 8),
                        ),
                      ),
                  ],
                ),
                activeIcon: const Icon(Icons.rate_review),
                label: 'Queue',
              ),
            BottomNavigationBarItem(
              icon: Stack(
                children: [
                  const Icon(Icons.notifications_outlined),
                  if (notifProvider.unreadCount > 0)
                    Positioned(
                      right: 0,
                      top: 0,
                      child: Container(
                        padding: const EdgeInsets.all(2),
                        decoration: const BoxDecoration(
                          color: AppConfig.dangerColor,
                          shape: BoxShape.circle,
                        ),
                        constraints: const BoxConstraints(minWidth: 8, minHeight: 8),
                      ),
                    ),
                ],
              ),
              activeIcon: const Icon(Icons.notifications),
              label: 'Alerts',
            ),
            const BottomNavigationBarItem(
              icon: Icon(Icons.settings_outlined),
              activeIcon: Icon(Icons.settings),
              label: 'Settings',
            ),
          ],
        ),
      ),
    );
  }
}
