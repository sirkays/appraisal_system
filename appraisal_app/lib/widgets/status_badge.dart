import 'package:flutter/material.dart';
import '../core/config.dart';

class StatusBadge extends StatelessWidget {
  final String status;
  final String? displayLabel;

  const StatusBadge({
    super.key,
    required this.status,
    this.displayLabel,
  });

  @override
  Widget build(BuildContext context) {
    Color badgeColor;
    Color textColor;
    String label = displayLabel ?? status;

    switch (status) {
      case 'NOT_STARTED':
      case 'DRAFT':
        badgeColor = AppConfig.surfaceColor;
        textColor = AppConfig.textSecondary;
        break;
      case 'SUBMITTED':
      case 'AWAITING_STEP_REVIEW':
      case 'UNDER_REVIEW':
        badgeColor = AppConfig.warningColor.withOpacity(0.18);
        textColor = AppConfig.warningColor;
        break;
      case 'RETURNED_TO_STAFF':
      case 'RETURNED_TO_REVIEWER':
        badgeColor = AppConfig.dangerColor.withOpacity(0.18);
        textColor = AppConfig.dangerColor;
        break;
      case 'APPROVED':
      case 'STAFF_ACKNOWLEDGED':
        badgeColor = AppConfig.accentColor.withOpacity(0.18);
        textColor = AppConfig.accentColor;
        break;
      default:
        badgeColor = AppConfig.secondaryColor.withOpacity(0.18);
        textColor = AppConfig.secondaryColor;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: badgeColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: textColor.withOpacity(0.4), width: 1),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: textColor,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
