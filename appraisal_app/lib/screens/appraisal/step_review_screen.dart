import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../providers/appraisal_provider.dart';
import '../../providers/reviewer_provider.dart';
import '../../models/form_model.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/dynamic_form_builder.dart';

class StepReviewScreen extends StatefulWidget {
  /// The full queue item — carries step labels, action button text, and appraisal ID.
  final ReviewQueueItem queueItem;

  const StepReviewScreen({super.key, required this.queueItem});

  @override
  State<StepReviewScreen> createState() => _StepReviewScreenState();
}

class _StepReviewScreenState extends State<StepReviewScreen> {
  final _commentController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final Map<int, GlobalKey> _fieldKeys = {};
  List<int> _fillableFieldIds = [];
  int _currentFocusedFieldIndex = -1;

  // reviewer-entered form field responses (reviewer-filled fields or Mode B scores)
  final Map<int, Map<String, dynamic>> _reviewerResponses = {};
  // Mode B per-field score override (reviewer_can_score)
  final Map<int, double> _modeBScores = {};
  // Mode B per-field comment override (reviewer_can_comment)
  final Map<int, String> _modeBComments = {};
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AppraisalProvider>(context, listen: false)
          .fetchAppraisalDetail(widget.queueItem.appraisal.id);
    });
  }

  @override
  void dispose() {
    _commentController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToNext() {
    if (_fillableFieldIds.isEmpty) return;
    _currentFocusedFieldIndex = (_currentFocusedFieldIndex + 1) % _fillableFieldIds.length;
    _scrollToField(_fillableFieldIds[_currentFocusedFieldIndex]);
  }

  void _scrollToPrev() {
    if (_fillableFieldIds.isEmpty) return;
    _currentFocusedFieldIndex = (_currentFocusedFieldIndex - 1) % _fillableFieldIds.length;
    if (_currentFocusedFieldIndex < 0) {
      _currentFocusedFieldIndex = _fillableFieldIds.length - 1;
    }
    _scrollToField(_fillableFieldIds[_currentFocusedFieldIndex]);
  }

  void _scrollToField(int fieldId) {
    final key = _fieldKeys[fieldId];
    if (key?.currentContext != null) {
      Scrollable.ensureVisible(
        key!.currentContext!,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
        alignment: 0.1, // Aligns slightly below top edge
      );
    }
  }

  void _onReviewerFieldChanged(Map<String, dynamic> data) {
    final fieldId = data['field_id'];
    _reviewerResponses[fieldId] = data;
  }

  /// Build the list of responses to send — includes reviewer-filled fields AND
  /// Mode B score/comment entries.
  List<Map<String, dynamic>> _buildResponses() {
    final responses = <Map<String, dynamic>>[];

    // Standard reviewer-filled fields
    for (final entry in _reviewerResponses.values) {
      responses.add({...entry, 'response_type': 'PRIMARY'});
    }

    // Mode B scores (REVIEWER_SCORE)
    for (final entry in _modeBScores.entries) {
      responses.add({
        'field_id': entry.key,
        'score': entry.value,
        'response_type': 'REVIEWER_SCORE',
      });
    }

    // Mode B comments (REVIEWER_COMMENT)
    for (final entry in _modeBComments.entries) {
      if (entry.value.trim().isNotEmpty) {
        responses.add({
          'field_id': entry.key,
          'text_response': entry.value,
          'response_type': 'REVIEWER_COMMENT',
        });
      }
    }

    return responses;
  }

  Future<void> _handleReviewAction(String action) async {
    if (action == 'SAVE_DRAFT') {
      setState(() => _submitting = true);
      final reviewerProvider =
          Provider.of<ReviewerProvider>(context, listen: false);

      final success = await reviewerProvider.submitStepReview(
        appraisalId: widget.queueItem.appraisal.id,
        action: 'SAVE_DRAFT',
        comments: _commentController.text.trim(),
        responses: _buildResponses(),
      );

      if (!mounted) return;
      setState(() => _submitting = false);

      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            backgroundColor: AppConfig.accentColor,
            content: Text('Review draft saved successfully!'),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppConfig.dangerColor,
            content:
                Text(reviewerProvider.errorMessage ?? 'Failed to save draft'),
          ),
        );
      }
      return;
    }

    // Confirmation dialog
    final actionLabel = action == 'APPROVE'
        ? widget.queueItem.actionLabelApprove
        : widget.queueItem.actionLabelReturn;

    final returnReasonController =
        TextEditingController(text: _commentController.text.trim());

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: context.cardColor,
        title: Text(
          action == 'APPROVE' ? 'Confirm Approval' : 'Return for Revision',
          style: TextStyle(
              color: context.textPrimary, fontWeight: FontWeight.bold),
        ),
        content: action == 'APPROVE'
            ? Text(
                'Are you sure you want to approve and forward this appraisal?',
                style: TextStyle(color: context.textSecondary, fontSize: 14),
              )
            : Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Are you sure you want to return this appraisal for revision?',
                    style:
                        TextStyle(color: context.textSecondary, fontSize: 14),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'Reason for Return (Optional):',
                    style: TextStyle(
                      color: context.textPrimary,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: returnReasonController,
                    maxLines: 3,
                    style: TextStyle(color: context.textPrimary, fontSize: 13),
                    decoration: InputDecoration(
                      hintText:
                          'Enter reason or feedback for staff/reviewer (optional)...',
                      hintStyle: TextStyle(
                          color: context.textSecondary.withAlpha(100),
                          fontSize: 12),
                      filled: true,
                      fillColor: context.surfaceColor.withAlpha(80),
                      contentPadding: const EdgeInsets.all(10),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: BorderSide(
                            color: context.textSecondary.withAlpha(30)),
                      ),
                    ),
                  ),
                ],
              ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child:
                Text('Cancel', style: TextStyle(color: context.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () {
              if (action == 'RETURN') {
                _commentController.text = returnReasonController.text.trim();
              }
              Navigator.pop(ctx, true);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: action == 'APPROVE'
                  ? AppConfig.accentColor
                  : AppConfig.dangerColor,
            ),
            child: Text(actionLabel,
                style: const TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    setState(() => _submitting = true);
    final reviewerProvider =
        Provider.of<ReviewerProvider>(context, listen: false);
    final appraisalProvider =
        Provider.of<AppraisalProvider>(context, listen: false);

    final success = await reviewerProvider.submitStepReview(
      appraisalId: widget.queueItem.appraisal.id,
      action: action,
      comments: _commentController.text.trim(),
      responses: _buildResponses(),
    );

    if (!mounted) return;
    setState(() => _submitting = false);

    if (success) {
      // Refresh dashboard in background
      appraisalProvider.fetchDashboard();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: AppConfig.accentColor,
          content: Text(
            action == 'APPROVE'
                ? '${widget.queueItem.actionLabelApprove} — done!'
                : '${widget.queueItem.actionLabelReturn} — done!',
          ),
        ),
      );
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: AppConfig.dangerColor,
          content:
              Text(reviewerProvider.errorMessage ?? 'Review action failed'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final appraisalProvider = Provider.of<AppraisalProvider>(context);
    final detail = appraisalProvider.activeAppraisalDetail;
    final item = widget.queueItem;

    // Compute fillable fields using allowedFilledByValues which resolves
    // STEP_N codes through the general process
    final allowed = item.allowedFilledByValues;
    List<int> currentFillableIds = [];
    if (detail != null) {
      for (var section in detail.sections) {
        for (var field in section.fields) {
          final isCurrentReviewerField = allowed.contains(field.filledBy);
          final hasModeBScore = field.reviewerCanScore &&
              (field.reviewerScoreRole == null ||
                  field.reviewerScoreRole!.isEmpty ||
                  allowed.contains(field.reviewerScoreRole));
          final hasModeBComment = field.reviewerCanComment &&
              (field.reviewerCommentRole == null ||
                  field.reviewerCommentRole!.isEmpty ||
                  allowed.contains(field.reviewerCommentRole));
                  
          if (isCurrentReviewerField || hasModeBScore || hasModeBComment) {
            currentFillableIds.add(field.id);
            _fieldKeys.putIfAbsent(field.id, () => GlobalKey());
          }
        }
      }
    }
    _fillableFieldIds = currentFillableIds;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          detail != null ? 'Review: ${detail.staff.fullName}' : 'Step Review',
          style: const TextStyle(fontSize: 16),
        ),
        actions: [
          TextButton.icon(
            onPressed: _submitting ? null : () => _handleReviewAction('SAVE_DRAFT'),
            icon: const Icon(Icons.save_outlined, size: 18, color: AppConfig.primaryColor),
            label: const Text(
              'Save Draft',
              style: TextStyle(
                color: AppConfig.primaryColor,
                fontWeight: FontWeight.bold,
                fontSize: 13,
              ),
            ),
          ),
          const SizedBox(width: 8),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(32),
          child: Container(
            width: double.infinity,
            color: AppConfig.primaryColor.withAlpha(20),
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            child: Text(
              'Step ${item.stepNumber}: ${item.stepLabel}',
              style: const TextStyle(
                color: AppConfig.primaryColor,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
      floatingActionButton: _fillableFieldIds.isEmpty ? null : Padding(
        padding: const EdgeInsets.only(bottom: 80.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            FloatingActionButton.small(
              heroTag: 'prevField',
              onPressed: _scrollToPrev,
              backgroundColor: AppConfig.primaryColor,
              child: const Icon(Icons.keyboard_arrow_up, color: Colors.white),
            ),
            const SizedBox(height: 8),
            FloatingActionButton.small(
              heroTag: 'nextField',
              onPressed: _scrollToNext,
              backgroundColor: AppConfig.primaryColor,
              child: const Icon(Icons.keyboard_arrow_down, color: Colors.white),
            ),
          ],
        ),
      ),
      body: appraisalProvider.isLoading || detail == null
          ? const Center(
              child:
                  SpinKitFadingCube(color: AppConfig.primaryColor, size: 40))
          : Column(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ── Staff summary header ───────────────────────
                        CustomCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                detail.staff.fullName,
                                style: TextStyle(
                                  color: context.textPrimary,
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Staff ID: ${detail.staff.staffId} • ${detail.staff.designation}',
                                style: TextStyle(
                                    color: context.textSecondary,
                                    fontSize: 13),
                              ),
                              Text(
                                'Department: ${detail.staff.departmentName ?? 'N/A'}',
                                style: TextStyle(
                                    color: context.textSecondary,
                                    fontSize: 13),
                              ),
                              if (detail.overallSelfScore != null) ...[
                                const SizedBox(height: 8),
                                Text(
                                  'Staff Self Score: ${detail.overallSelfScore!.toStringAsFixed(2)} / 100',
                                  style: const TextStyle(
                                      color: AppConfig.accentColor,
                                      fontWeight: FontWeight.bold),
                                ),
                              ],
                            ],
                          ),
                        ),

                        // ── Return Reason Banner (if returned for revision) ──
                        if (detail.returnNotes != null && detail.returnNotes!.isNotEmpty) ...[
                          const SizedBox(height: 14),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppConfig.warningColor.withAlpha(25),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppConfig.warningColor.withAlpha(80)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.warning_amber_rounded, color: AppConfig.warningColor, size: 20),
                                    const SizedBox(width: 8),
                                    Text(
                                      'Returned for Re-review',
                                      style: TextStyle(
                                        color: context.textPrimary,
                                        fontSize: 14,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'Reason: ${detail.returnNotes}',
                                  style: TextStyle(
                                    color: context.textPrimary,
                                    fontSize: 13,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                        const SizedBox(height: 20),

                        // ── Form sections ─────────────────────────────
                        ...detail.sections.map((section) {
                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Section header
                              Padding(
                                padding:
                                    const EdgeInsets.only(bottom: 12),
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      section.name,
                                      style: const TextStyle(
                                        color: AppConfig.secondaryColor,
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    if (section.description.isNotEmpty)
                                      Text(
                                        section.description,
                                        style: TextStyle(
                                            color: context.textSecondary,
                                            fontSize: 12),
                                      ),
                                  ],
                                ),
                              ),

                              ...section.fields.map((field) {
                                // ── Role-scoped field access control ──────
                                // Uses allowedFilledByValues which resolves
                                // STEP_N through the general process.

                                // Is this field assigned to THIS reviewer?
                                final isCurrentReviewerField =
                                    item.allowedFilledByValues.contains(field.filledBy);

                                // Is it assigned to a DIFFERENT reviewer role
                                // (not the appraisee and not this reviewer)?
                                final isOtherReviewerField =
                                    field.filledBy != 'APPRAISEE' &&
                                    !isCurrentReviewerField;

                                // Mode B: only show if the score/comment role
                                // matches this reviewer's role (or no role set).
                                final hasModeBScore = field.reviewerCanScore &&
                                    (field.reviewerScoreRole == null ||
                                        field.reviewerScoreRole!.isEmpty ||
                                        item.allowedFilledByValues.contains(field.reviewerScoreRole));
                                final hasModeBComment = field.reviewerCanComment &&
                                    (field.reviewerCommentRole == null ||
                                        field.reviewerCommentRole!.isEmpty ||
                                        item.allowedFilledByValues.contains(field.reviewerCommentRole));

                                Widget childWidget;

                                // ── Case 1: This reviewer fills this field ──
                                if (isCurrentReviewerField) {
                                  final reviewerResponse =
                                      detail.formResponses.firstWhere(
                                    (r) =>
                                        r.fieldId == field.id &&
                                        r.responseType == 'PRIMARY',
                                    orElse: () => FormFieldResponseModel(
                                      id: 0,
                                      fieldId: field.id,
                                      responseType: 'PRIMARY',
                                      textResponse: '',
                                      selectedOptions: [],
                                    ),
                                  );

                                  childWidget = Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Padding(
                                        padding: const EdgeInsets.only(
                                            top: 8, bottom: 4),
                                        child: Text(
                                          'Your Assessment / Score:',
                                          style: const TextStyle(
                                            color: AppConfig.primaryColor,
                                            fontWeight: FontWeight.bold,
                                            fontSize: 13,
                                          ),
                                        ),
                                      ),
                                      DynamicFormFieldWidget(
                                        field: field,
                                        existingResponse:
                                            reviewerResponse.id != 0
                                                ? reviewerResponse
                                                : null,
                                        readOnly: false,
                                        onChanged: _onReviewerFieldChanged,
                                      ),
                                    ],
                                  );
                                }
                                // ── Case 2: Another reviewer's field — show
                                //    read-only so context is visible ──────────
                                else if (isOtherReviewerField) {
                                  final otherResponse =
                                      detail.formResponses.firstWhere(
                                    (r) =>
                                        r.fieldId == field.id &&
                                        r.responseType == 'PRIMARY',
                                    orElse: () => FormFieldResponseModel(
                                      id: 0,
                                      fieldId: field.id,
                                      responseType: 'PRIMARY',
                                      textResponse: '',
                                      selectedOptions: [],
                                    ),
                                  );

                                  childWidget = Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Padding(
                                        padding: const EdgeInsets.only(
                                            top: 8, bottom: 2),
                                        child: Row(
                                          children: [
                                            const Icon(
                                              Icons.lock_outline,
                                              size: 13,
                                              color: AppConfig.secondaryColor,
                                            ),
                                            const SizedBox(width: 4),
                                            Text(
                                              'Filled by: ${field.filledBy}',
                                              style: const TextStyle(
                                                color: AppConfig.secondaryColor,
                                                fontSize: 12,
                                                fontStyle: FontStyle.italic,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      DynamicFormFieldWidget(
                                        field: field,
                                        existingResponse:
                                            otherResponse.id != 0
                                                ? otherResponse
                                                : null,
                                        readOnly: true,
                                        onChanged: (_) {},
                                      ),
                                    ],
                                  );
                                }
                                // ── Case 3: Appraisee field — read-only with
                                //    optional Mode B score/comment ───────────
                                else {
                                  final staffResponse =
                                      detail.formResponses.firstWhere(
                                    (r) =>
                                        r.fieldId == field.id &&
                                        r.responseType == 'PRIMARY',
                                    orElse: () => FormFieldResponseModel(
                                      id: 0,
                                      fieldId: field.id,
                                      responseType: 'PRIMARY',
                                      textResponse: '',
                                      selectedOptions: [],
                                    ),
                                  );

                                  childWidget = Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      // Staff response (read-only)
                                      DynamicFormFieldWidget(
                                        field: field,
                                        existingResponse: staffResponse.id != 0
                                            ? staffResponse
                                            : null,
                                        readOnly: true,
                                        onChanged: (_) {},
                                      ),

                                      // Mode B — reviewer score (role-gated)
                                      if (hasModeBScore) ...[  
                                        _buildModeBScoreWidget(field),
                                      ],

                                      // Mode B — reviewer comment (role-gated)
                                      if (hasModeBComment) ...[  
                                        _buildModeBCommentWidget(field),
                                      ],
                                    ],
                                  );
                                }

                                final isFillable = _fillableFieldIds.contains(field.id);
                                final fieldKey = _fieldKeys[field.id];

                                return Container(
                                  key: fieldKey,
                                  margin: const EdgeInsets.only(bottom: 16),
                                  padding: isFillable ? const EdgeInsets.all(12) : EdgeInsets.zero,
                                  decoration: isFillable ? BoxDecoration(
                                    color: AppConfig.primaryColor.withAlpha(15),
                                    border: Border.all(color: AppConfig.primaryColor.withAlpha(100), width: 1.5),
                                    borderRadius: BorderRadius.circular(12),
                                  ) : null,
                                  child: childWidget,
                                );
                              }),
                              const SizedBox(height: 16),
                            ],
                          );
                        }),

                        // ── Overall comments ──────────────────────────
                        Text(
                          'Overall Comments / Feedback:',
                          style: TextStyle(
                              color: context.textPrimary,
                              fontWeight: FontWeight.bold,
                              fontSize: 15),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _commentController,
                          maxLines: 4,
                          style: TextStyle(color: context.textPrimary),
                          decoration: InputDecoration(
                            hintText:
                                'Add overall reviewer remarks or feedback...',
                            hintStyle: TextStyle(
                                color:
                                    context.textSecondary.withAlpha(100)),
                            filled: true,
                            fillColor: context.cardColor,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(
                                  color:
                                      context.textSecondary.withAlpha(30)),
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),
                      ],
                    ),
                  ),
                ),

                // ── Reviewer action buttons ────────────────────────────
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: context.cardColor,
                    boxShadow: [
                      BoxShadow(
                          color: Colors.black.withAlpha(30),
                          blurRadius: 10),
                    ],
                  ),
                  child: _submitting
                      ? const Center(
                          child: SpinKitFadingCube(
                              color: AppConfig.primaryColor, size: 28))
                      : Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton(
                                    onPressed: () =>
                                        _handleReviewAction('RETURN'),
                                    style: OutlinedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 14),
                                      side: const BorderSide(
                                          color: AppConfig.dangerColor),
                                      shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(12)),
                                    ),
                                    child: Text(
                                      item.actionLabelReturn,
                                      style: const TextStyle(
                                          color: AppConfig.dangerColor,
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: ElevatedButton(
                                    onPressed: () =>
                                        _handleReviewAction('APPROVE'),
                                    style: ElevatedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 14),
                                      backgroundColor: AppConfig.accentColor,
                                      shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(12)),
                                    ),
                                    child: Text(
                                      item.actionLabelApprove,
                                      style: const TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                ),
              ],
            ),
    );
  }

  // ── Mode B widgets ──────────────────────────────────────────────────────────

  Widget _buildModeBScoreWidget(FormFieldModel field) {
    final max = field.reviewerScoreMax ?? field.maxScore;
    final current = _modeBScores[field.id] ?? field.minScore;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppConfig.primaryColor.withAlpha(15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppConfig.primaryColor.withAlpha(60)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Your Score for this Field:',
            style: TextStyle(
              color: AppConfig.primaryColor,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Score: ${current.toStringAsFixed(1)} / ${max.toStringAsFixed(0)}',
                style: const TextStyle(
                    color: AppConfig.secondaryColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 14),
              ),
              Text(
                'Min: ${field.minScore.toStringAsFixed(0)}',
                style: TextStyle(
                    color: context.textSecondary, fontSize: 12),
              ),
            ],
          ),
          Slider(
            value: current.clamp(field.minScore, max),
            min: field.minScore,
            max: max,
            divisions:
                ((max - field.minScore) * 2).toInt().clamp(1, 100),
            activeColor: AppConfig.primaryColor,
            inactiveColor: context.textSecondary.withAlpha(40),
            onChanged: (val) {
              setState(() => _modeBScores[field.id] = val);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildModeBCommentWidget(FormFieldModel field) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppConfig.secondaryColor.withAlpha(15),
        borderRadius: BorderRadius.circular(12),
        border:
            Border.all(color: AppConfig.secondaryColor.withAlpha(60)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Your Comment on this Field:',
            style: TextStyle(
              color: AppConfig.secondaryColor,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            onChanged: (val) => _modeBComments[field.id] = val,
            maxLines: 3,
            style: TextStyle(color: context.textPrimary, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'Enter your comment on staff response...',
              hintStyle:
                  TextStyle(color: context.textSecondary.withAlpha(100)),
              filled: true,
              fillColor: context.cardColor,
              contentPadding: const EdgeInsets.all(10),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide(
                    color: context.textSecondary.withAlpha(30)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
