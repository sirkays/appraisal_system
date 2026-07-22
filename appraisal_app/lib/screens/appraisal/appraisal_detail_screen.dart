import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../providers/appraisal_provider.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/status_badge.dart';
import 'return_history_screen.dart';

class AppraisalDetailScreen extends StatefulWidget {
  final int appraisalId;

  const AppraisalDetailScreen({super.key, required this.appraisalId});

  @override
  State<AppraisalDetailScreen> createState() => _AppraisalDetailScreenState();
}

class _AppraisalDetailScreenState extends State<AppraisalDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AppraisalProvider>(context, listen: false)
          .fetchAppraisalDetail(widget.appraisalId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final appraisalProvider = Provider.of<AppraisalProvider>(context);
    final detail = appraisalProvider.activeAppraisalDetail;
    final currentUser = Provider.of<AuthProvider>(context, listen: false).user;

    // Is the logged-in user the owner/appraisee?
    final bool isOwner = currentUser != null && detail != null &&
        detail.staff.id == currentUser.id;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Appraisal Details'),
      ),
      body: appraisalProvider.isLoading || detail == null
          ? const Center(child: SpinKitFadingCube(color: AppConfig.primaryColor, size: 40))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header summary card
                  CustomCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            StatusBadge(
                              status: detail.status,
                              displayLabel: detail.statusDisplay,
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          detail.cycle.name,
                          style: TextStyle(
                            color: context.textPrimary,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Staff: ${detail.staff.fullName} (${detail.staff.staffId})',
                          style: TextStyle(color: context.textSecondary, fontSize: 13),
                        ),
                        Text(
                          'Department: ${detail.staff.departmentName ?? 'N/A'}',
                          style: TextStyle(color: context.textSecondary, fontSize: 13),
                        ),
                        Divider(color: context.textSecondary.withAlpha(30), height: 24),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            Column(
                              children: [
                                Text('Self Score', style: TextStyle(color: context.textSecondary, fontSize: 12)),
                                const SizedBox(height: 4),
                                Text(
                                  detail.overallSelfScore != null ? '${detail.overallSelfScore}' : 'N/A',
                                  style: const TextStyle(color: AppConfig.accentColor, fontSize: 20, fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                            Column(
                              children: [
                                Text('Supervisor Score', style: TextStyle(color: context.textSecondary, fontSize: 12)),
                                const SizedBox(height: 4),
                                Text(
                                  detail.overallSupervisorScore != null ? '${detail.overallSupervisorScore}' : 'N/A',
                                  style: const TextStyle(color: AppConfig.secondaryColor, fontSize: 20, fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // ── Acknowledge Action Card — only for the appraisee/owner ──
                  if (detail.canAcknowledge && isOwner) ...[
                    CustomCard(
                      color: AppConfig.accentColor.withAlpha(35),
                      border: Border.all(color: AppConfig.accentColor),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Action Required: Acknowledge Result',
                            style: TextStyle(color: AppConfig.accentColor, fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Your appraisal review has been completed and approved. Please acknowledge that you have reviewed the final score.',
                            style: TextStyle(color: context.textSecondary, fontSize: 13),
                          ),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: () async {
                                final success = await appraisalProvider.acknowledgeAppraisal(detail.id);
                                if (mounted && success) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Appraisal acknowledged!')),
                                  );
                                }
                              },
                              style: ElevatedButton.styleFrom(backgroundColor: AppConfig.accentColor),
                              child: const Text('I Acknowledge This Result', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],

                  // ── Return Reason / Notes Card — show ALL return comments from any reviewer ──
                  // Collect all RETURNED assignments with comments
                  if (detail.approvalAssignments.any((a) => a.status == 'RETURNED' && a.comments.isNotEmpty) ||
                      (detail.returnNotes != null && detail.returnNotes!.isNotEmpty)) ...[
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppConfig.warningColor.withAlpha(25),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: AppConfig.warningColor.withAlpha(100)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.info_outline, color: AppConfig.warningColor, size: 18),
                              const SizedBox(width: 8),
                              Text(
                                'Return Reasons / Reviewer Notes',
                                style: const TextStyle(
                                  color: AppConfig.warningColor,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          // Show each returned assignment's comment separately
                          ...detail.approvalAssignments
                              .where((a) => a.status == 'RETURNED' && a.comments.isNotEmpty)
                              .map((a) => Padding(
                                    padding: const EdgeInsets.only(bottom: 8),
                                    child: Row(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Container(
                                          margin: const EdgeInsets.only(top: 4, right: 8),
                                          width: 7,
                                          height: 7,
                                          decoration: BoxDecoration(
                                            color: AppConfig.warningColor,
                                            shape: BoxShape.circle,
                                          ),
                                        ),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                '${a.step?.label ?? 'Reviewer'}: ${a.approverName ?? ''}',
                                                style: TextStyle(
                                                  color: context.textSecondary,
                                                  fontSize: 11,
                                                  fontWeight: FontWeight.w600,
                                                ),
                                              ),
                                              const SizedBox(height: 2),
                                              Text(
                                                a.comments,
                                                style: TextStyle(color: context.textPrimary, fontSize: 13),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
                                  )),
                          // Fallback to returnNotes if no assignment comments found
                          if (detail.approvalAssignments.every((a) => a.status != 'RETURNED' || a.comments.isEmpty) &&
                              detail.returnNotes != null &&
                              detail.returnNotes!.isNotEmpty)
                            Text(
                              detail.returnNotes!,
                              style: TextStyle(color: context.textPrimary, fontSize: 13),
                            ),
                          const SizedBox(height: 12),
                          // Dedicated button to view full return history
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton.icon(
                              onPressed: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => ReturnHistoryScreen(
                                    appraisalId: detail.id,
                                    staffName: detail.staff.fullName,
                                  ),
                                ),
                              ),
                              icon: const Icon(Icons.history, size: 16, color: AppConfig.warningColor),
                              label: const Text(
                                'View Full Return History',
                                style: TextStyle(color: AppConfig.warningColor, fontWeight: FontWeight.bold),
                              ),
                              style: OutlinedButton.styleFrom(
                                side: const BorderSide(color: AppConfig.warningColor),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],

                  // Step Review History Timeline
                  Text(
                    'Approval Workflow History',
                    style: TextStyle(color: context.textPrimary, fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),

                  if (detail.approvalAssignments.isEmpty)
                    Text('No review steps configured.', style: TextStyle(color: context.textSecondary))
                  else
                    ...detail.approvalAssignments.map((ass) {
                      return Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: context.surfaceColor.withAlpha(120),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: ass.status == 'RETURNED'
                                ? AppConfig.warningColor.withAlpha(80)
                                : context.textSecondary.withAlpha(30),
                          ),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            CircleAvatar(
                              radius: 14,
                              backgroundColor: ass.status == 'APPROVED'
                                  ? AppConfig.accentColor
                                  : ass.status == 'RETURNED'
                                      ? AppConfig.warningColor
                                      : context.surfaceColor,
                              child: Text(
                                '${ass.step?.stepNumber ?? 1}',
                                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Flexible(
                                        child: Text(
                                          ass.step?.label ?? 'Step',
                                          style: TextStyle(color: context.textPrimary, fontWeight: FontWeight.bold, fontSize: 14),
                                        ),
                                      ),
                                      StatusBadge(status: ass.status),
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Approver: ${ass.approverName ?? 'Unassigned'}',
                                    style: TextStyle(color: context.textSecondary, fontSize: 12),
                                  ),
                                  // Always show comments — approvals AND returns
                                  if (ass.comments.isNotEmpty) ...[
                                    const SizedBox(height: 6),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                      decoration: BoxDecoration(
                                        color: ass.status == 'RETURNED'
                                            ? AppConfig.warningColor.withAlpha(20)
                                            : AppConfig.primaryColor.withAlpha(15),
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Text(
                                        ass.status == 'RETURNED'
                                            ? '⚠ Return Reason: "${ass.comments}"'
                                            : 'Comments: "${ass.comments}"',
                                        style: TextStyle(
                                          color: ass.status == 'RETURNED' ? AppConfig.warningColor : AppConfig.secondaryColor,
                                          fontSize: 12,
                                          fontStyle: FontStyle.italic,
                                        ),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    }),
                ],
              ),
            ),
    );
  }
}
