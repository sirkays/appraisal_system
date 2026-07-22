import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/custom_card.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<NotificationProvider>(context, listen: false).fetchNotifications();
    });
  }

  @override
  Widget build(BuildContext context) {
    final notifProvider = Provider.of<NotificationProvider>(context);

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text('Notifications'),
      ),
      body: notifProvider.isLoading
          ? const Center(child: SpinKitFadingCube(color: AppConfig.primaryColor, size: 40))
          : notifProvider.notifications.isEmpty
              ? Center(
                  child: Text(
                    'No notifications.',
                    style: TextStyle(color: context.textSecondary),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: notifProvider.notifications.length,
                  itemBuilder: (context, index) {
                    final notif = notifProvider.notifications[index];

                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: CustomCard(
                        color: notif.isRead
                            ? context.cardColor
                            : context.surfaceColor.withAlpha(150),
                        border: notif.isRead
                            ? null
                            : Border.all(color: AppConfig.primaryColor.withAlpha(120)),
                        onTap: () {
                          if (!notif.isRead) {
                            notifProvider.markAsRead(notif.id);
                          }
                        },
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: notif.isRead
                                    ? context.textSecondary.withAlpha(30)
                                    : AppConfig.primaryColor.withAlpha(40),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                notif.isRead ? Icons.notifications_none : Icons.notifications_active,
                                color: notif.isRead ? context.textSecondary : AppConfig.primaryColor,
                                size: 20,
                              ),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    notif.title,
                                    style: TextStyle(
                                      color: context.textPrimary,
                                      fontWeight: notif.isRead ? FontWeight.normal : FontWeight.bold,
                                      fontSize: 15,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    notif.message,
                                    style: TextStyle(color: context.textSecondary, fontSize: 13),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    notif.createdAt,
                                    style: TextStyle(color: context.textSecondary.withAlpha(120), fontSize: 11),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
