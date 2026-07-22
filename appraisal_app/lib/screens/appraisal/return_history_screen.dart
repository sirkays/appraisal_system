import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../core/api_service.dart';
import '../../core/config.dart';
import '../../widgets/custom_card.dart';

class ReturnHistoryModel {
  final int id;
  final String reviewerName;
  final String stepLabel;
  final int fromStepNumber;
  final int toStepNumber;
  final String toLabel;
  final String reason;
  final DateTime returnedAt;

  ReturnHistoryModel({
    required this.id,
    required this.reviewerName,
    required this.stepLabel,
    required this.fromStepNumber,
    required this.toStepNumber,
    required this.toLabel,
    required this.reason,
    required this.returnedAt,
  });

  factory ReturnHistoryModel.fromJson(Map<String, dynamic> json) {
    return ReturnHistoryModel(
      id: json['id'] ?? 0,
      reviewerName: json['reviewer_name'] ?? 'Unknown',
      stepLabel: json['step_label'] ?? 'Step',
      fromStepNumber: json['from_step_number'] ?? 0,
      toStepNumber: json['to_step_number'] ?? 0,
      toLabel: json['to_label'] ?? '',
      reason: json['reason'] ?? '',
      returnedAt: DateTime.tryParse(json['returned_at'] ?? '') ?? DateTime.now(),
    );
  }
}

class ReturnHistoryScreen extends StatefulWidget {
  final int appraisalId;
  final String staffName;

  const ReturnHistoryScreen({
    super.key,
    required this.appraisalId,
    required this.staffName,
  });

  @override
  State<ReturnHistoryScreen> createState() => _ReturnHistoryScreenState();
}

class _ReturnHistoryScreenState extends State<ReturnHistoryScreen> {
  bool _loading = true;
  String? _error;
  List<ReturnHistoryModel> _logs = [];

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    setState(() { _loading = true; _error = null; });
    try {
      final res = await ApiService().get('/appraisals/${widget.appraisalId}/return-history/');
      final list = (res['return_history'] as List? ?? []);
      setState(() {
        _logs = list.map((j) => ReturnHistoryModel.fromJson(j)).toList();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceAll('Exception: ', '');
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Return History', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text(widget.staffName, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.normal)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchHistory,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppConfig.primaryColor))
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.error_outline, color: AppConfig.dangerColor, size: 48),
                        const SizedBox(height: 12),
                        Text(_error!, textAlign: TextAlign.center, style: TextStyle(color: context.textPrimary)),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: _fetchHistory,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : _logs.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.check_circle_outline, color: AppConfig.primaryColor, size: 64),
                          const SizedBox(height: 16),
                          Text(
                            'No returns recorded',
                            style: TextStyle(
                              color: context.textPrimary,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'This appraisal has not been returned by any reviewer.',
                            style: TextStyle(color: context.textSecondary, fontSize: 14),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      color: AppConfig.primaryColor,
                      onRefresh: _fetchHistory,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _logs.length,
                        itemBuilder: (context, index) {
                          final log = _logs[index];
                          final formattedDate = DateFormat('d MMM yyyy, HH:mm').format(
                            log.returnedAt.toLocal(),
                          );
                          final isToStaff = log.toStepNumber == 0;

                          return Container(
                            margin: const EdgeInsets.only(bottom: 14),
                            child: CustomCard(
                              color: AppConfig.warningColor.withAlpha(18),
                              border: Border.all(color: AppConfig.warningColor.withAlpha(70)),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Header row with number badge and date
                                  Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        width: 36,
                                        height: 36,
                                        decoration: BoxDecoration(
                                          color: AppConfig.warningColor,
                                          shape: BoxShape.circle,
                                        ),
                                        child: Center(
                                          child: Text(
                                            '${_logs.length - index}',
                                            style: const TextStyle(
                                              color: Colors.white,
                                              fontWeight: FontWeight.bold,
                                              fontSize: 14,
                                            ),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              log.reviewerName,
                                              style: TextStyle(
                                                color: context.textPrimary,
                                                fontWeight: FontWeight.bold,
                                                fontSize: 15,
                                              ),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              formattedDate,
                                              style: TextStyle(
                                                color: context.textSecondary,
                                                fontSize: 12,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: AppConfig.warningColor.withAlpha(40),
                                          borderRadius: BorderRadius.circular(20),
                                        ),
                                        child: Text(
                                          'RETURNED',
                                          style: const TextStyle(
                                            color: AppConfig.warningColor,
                                            fontSize: 11,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  const Divider(height: 1),
                                  const SizedBox(height: 12),

                                  // Step flow info
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              'Returned from',
                                              style: TextStyle(color: context.textSecondary, fontSize: 11),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              log.stepLabel,
                                              style: TextStyle(
                                                color: context.textPrimary,
                                                fontSize: 13,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      const Icon(Icons.arrow_forward, size: 18, color: AppConfig.warningColor),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.end,
                                          children: [
                                            Text(
                                              'Returned to',
                                              style: TextStyle(color: context.textSecondary, fontSize: 11),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              log.toLabel,
                                              textAlign: TextAlign.end,
                                              style: TextStyle(
                                                color: isToStaff ? AppConfig.dangerColor : AppConfig.primaryColor,
                                                fontSize: 13,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),

                                  // Reason text
                                  Container(
                                    width: double.infinity,
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: context.surfaceColor,
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          '⚠  Reason / Comment',
                                          style: TextStyle(
                                            color: context.textSecondary,
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          log.reason.isNotEmpty ? log.reason : '(No reason provided)',
                                          style: TextStyle(
                                            color: log.reason.isNotEmpty
                                                ? context.textPrimary
                                                : context.textSecondary,
                                            fontSize: 14,
                                            fontStyle: log.reason.isEmpty ? FontStyle.italic : FontStyle.normal,
                                          ),
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
                    ),
    );
  }
}
