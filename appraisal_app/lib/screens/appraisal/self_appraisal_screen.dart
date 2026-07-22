import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../providers/appraisal_provider.dart';
import '../../models/form_model.dart';
import '../../widgets/dynamic_form_builder.dart';
import '../../widgets/custom_card.dart';

class SelfAppraisalScreen extends StatefulWidget {
  final int appraisalId;

  const SelfAppraisalScreen({super.key, required this.appraisalId});

  @override
  State<SelfAppraisalScreen> createState() => _SelfAppraisalScreenState();
}

class _SelfAppraisalScreenState extends State<SelfAppraisalScreen> {
  final Map<int, Map<String, dynamic>> _formResponses = {};
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AppraisalProvider>(context, listen: false)
          .fetchAppraisalDetail(widget.appraisalId);
    });
  }

  void _onFieldChanged(Map<String, dynamic> responseData) {
    final fieldId = responseData['field_id'];
    _formResponses[fieldId] = responseData;
  }

  /// Validate required fields and return a list of missing field labels.
  List<String> _validateRequiredFields(
      List<dynamic> sections, List<dynamic> formResponses) {
    final missing = <String>[];
    for (final section in sections) {
      for (final field in section.fields) {
        if (field.filledBy != 'APPRAISEE') continue;
        if (!field.isRequired) continue;

        final localResponse = _formResponses[field.id];
        final existingResponse = formResponses.firstWhere(
          (r) => r.fieldId == field.id && r.responseType == 'PRIMARY',
          orElse: () => FormFieldResponseModel(
            id: 0,
            fieldId: field.id,
            responseType: 'PRIMARY',
            textResponse: '',
            selectedOptions: [],
          ),
        );

        // Use the most up-to-date value (local change > existing)
        final text = localResponse?['text_response'] as String? ??
            (existingResponse.id != 0 ? existingResponse.textResponse : '');
        final score = localResponse?['score'] as double?;
        final scoreFromExisting = existingResponse.id != 0 ? existingResponse.score : null;
        final options = localResponse?['selected_options'] as List? ??
            (existingResponse.id != 0 ? existingResponse.selectedOptions : []);

        bool isFilled = false;
        switch (field.fieldType) {
          case 'NARRATIVE':
            isFilled = text.trim().isNotEmpty;
            break;
          case 'SCORE':
          case 'SCORE_COMMENT':
            // A score of 0 is still a valid response
            isFilled = (score != null) || (scoreFromExisting != null);
            break;
          case 'SINGLE_SELECT':
          case 'MULTI_SELECT':
            isFilled = (options as List).isNotEmpty;
            break;
          default:
            isFilled = true;
        }

        if (!isFilled) missing.add(field.label);
      }
    }
    return missing;
  }

  Future<void> _handleSave(String action) async {
    final appraisalProvider =
        Provider.of<AppraisalProvider>(context, listen: false);
    final detail = appraisalProvider.activeAppraisalDetail;
    if (detail == null) return;

    // Validate on submit
    if (action == 'submit') {
      final missing = _validateRequiredFields(detail.sections, detail.formResponses);
      if (missing.isNotEmpty) {
        if (!mounted) return;
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: context.cardColor,
            title: Text(
              'Required Fields Missing',
              style:
                  TextStyle(color: context.textPrimary, fontWeight: FontWeight.bold),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Please fill in all required fields before submitting:',
                  style:
                      TextStyle(color: context.textSecondary, fontSize: 13),
                ),
                const SizedBox(height: 12),
                ...missing.take(5).map((f) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Row(
                        children: [
                          const Icon(Icons.circle,
                              size: 6, color: AppConfig.dangerColor),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(f,
                                style: const TextStyle(
                                    color: AppConfig.dangerColor,
                                    fontSize: 13)),
                          ),
                        ],
                      ),
                    )),
                if (missing.length > 5)
                  Text(
                    '… and ${missing.length - 5} more',
                    style: const TextStyle(
                        color: AppConfig.dangerColor, fontSize: 12),
                  ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('OK',
                    style: TextStyle(color: AppConfig.primaryColor)),
              ),
            ],
          ),
        );
        return;
      }

      // Confirmation dialog
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: context.cardColor,
          title: Text(
            'Submit Appraisal?',
            style: TextStyle(
                color: context.textPrimary, fontWeight: FontWeight.bold),
          ),
          content: Text(
            'Once submitted, you will not be able to make changes until your reviewer returns it. Are you sure you want to submit?',
            style: TextStyle(color: context.textSecondary, fontSize: 14),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text('Cancel',
                  style: TextStyle(color: context.textSecondary)),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: ElevatedButton.styleFrom(
                  backgroundColor: AppConfig.primaryColor),
              child: const Text('Submit',
                  style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      );
      if (confirmed != true || !mounted) return;
    }

    setState(() => _submitting = true);
    final responsesList = _formResponses.values.toList();

    final success = await appraisalProvider.submitSelfAppraisal(
      widget.appraisalId,
      action,
      responsesList,
    );

    if (!mounted) return;
    setState(() => _submitting = false);

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            action == 'submit'
                ? 'Appraisal submitted successfully!'
                : 'Draft saved successfully!',
          ),
          backgroundColor: AppConfig.accentColor,
        ),
      );
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: AppConfig.dangerColor,
          content: Text(appraisalProvider.errorMessage ?? 'Submission failed'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final appraisalProvider = Provider.of<AppraisalProvider>(context);
    final detail = appraisalProvider.activeAppraisalDetail;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          detail != null
              ? 'Self Assessment — ${detail.cycle.name}'
              : 'Self Assessment',
          style: const TextStyle(fontSize: 16),
        ),
      ),
      body: appraisalProvider.isLoading || detail == null
          ? const Center(
              child: SpinKitFadingCube(
                  color: AppConfig.primaryColor, size: 40))
          : !detail.canEdit
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.lock_outline,
                            size: 48, color: AppConfig.secondaryColor),
                        const SizedBox(height: 12),
                        Text(
                          'Appraisal Locked',
                          style: TextStyle(
                              color: context.textPrimary,
                              fontSize: 18,
                              fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'This appraisal has already been submitted and is currently under review.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                              color: context.textSecondary, fontSize: 14),
                        ),
                      ],
                    ),
                  ),
                )
              : Column(
                  children: [
                    // Return notes banner (when revision requested)
                    if (detail.returnNotes != null &&
                        detail.returnNotes!.isNotEmpty)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        color: AppConfig.warningColor.withAlpha(25),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.warning_amber_rounded,
                                color: AppConfig.warningColor, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Returned: ${detail.returnNotes}',
                                style: const TextStyle(
                                  color: AppConfig.warningColor,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                    Expanded(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: detail.sections.map((section) {
                            final appraiseeFields = section.fields
                                .where((f) => f.filledBy == 'APPRAISEE')
                                .toList();

                            if (appraiseeFields.isEmpty) {
                              return const SizedBox.shrink();
                            }

                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                CustomCard(
                                  color:
                                      AppConfig.primaryColor.withAlpha(30),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        section.name,
                                        style: TextStyle(
                                          color: context.textPrimary,
                                          fontSize: 17,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      if (section.description
                                          .isNotEmpty) ...[
                                        const SizedBox(height: 4),
                                        Text(
                                          section.description,
                                          style: TextStyle(
                                              color: context.textSecondary,
                                              fontSize: 12),
                                        ),
                                      ],
                                      if (section.sectionWeight > 0) ...[
                                        const SizedBox(height: 4),
                                        Text(
                                          'Weight: ${section.sectionWeight.toStringAsFixed(0)}%',
                                          style: const TextStyle(
                                              color: AppConfig.accentColor,
                                              fontSize: 12,
                                              fontWeight: FontWeight.bold),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 16),
                                ...appraiseeFields.map((field) {
                                  final existing =
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

                                  return DynamicFormFieldWidget(
                                    field: field,
                                    appraisalId: detail.id,
                                    existingResponse:
                                        existing.id != 0 ? existing : null,
                                    onChanged: _onFieldChanged,
                                  );
                                }),
                                const SizedBox(height: 24),
                              ],
                            );
                          }).toList(),
                        ),
                      ),
                    ),

                    // ── Bottom Action Buttons ──────────────────────────
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
                          : Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton(
                                    onPressed: () => _handleSave('draft'),
                                    style: OutlinedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 14),
                                      side: BorderSide(
                                          color: context.textSecondary),
                                      shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(12)),
                                    ),
                                    child: Text('Save Draft',
                                        style: TextStyle(
                                            color: context.textPrimary)),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: ElevatedButton(
                                    onPressed: () => _handleSave('submit'),
                                    style: ElevatedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 14),
                                      backgroundColor: AppConfig.primaryColor,
                                      shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(12)),
                                    ),
                                    child: const Text(
                                      'Submit Appraisal',
                                      style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                    ),
                  ],
                ),
    );
  }
}
