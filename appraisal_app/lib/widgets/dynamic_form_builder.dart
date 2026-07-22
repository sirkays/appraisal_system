import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../core/config.dart';
import '../core/api_service.dart';
import '../models/form_model.dart';

class DynamicFormFieldWidget extends StatefulWidget {
  final FormFieldModel field;
  final FormFieldResponseModel? existingResponse;
  final int? appraisalId;
  final bool readOnly;
  final Function(Map<String, dynamic> responseData) onChanged;

  const DynamicFormFieldWidget({
    super.key,
    required this.field,
    this.existingResponse,
    this.appraisalId,
    this.readOnly = false,
    required this.onChanged,
  });

  @override
  State<DynamicFormFieldWidget> createState() => _DynamicFormFieldWidgetState();
}

class _DynamicFormFieldWidgetState extends State<DynamicFormFieldWidget> {
  late TextEditingController _textController;
  late double _scoreValue;
  late List<String> _selectedOptions;
  bool _isUploadingFile = false;
  String? _evidenceFileUrl;
  String? _uploadedFileName;

  @override
  void initState() {
    super.initState();
    _textController = TextEditingController(
      text: widget.existingResponse?.textResponse ?? '',
    );
    _scoreValue = widget.existingResponse?.score ?? widget.field.minScore;
    if (_scoreValue < widget.field.minScore) _scoreValue = widget.field.minScore;
    if (_scoreValue > widget.field.maxScore) _scoreValue = widget.field.maxScore;

    _selectedOptions = List<String>.from(widget.existingResponse?.selectedOptions ?? []);
    _evidenceFileUrl = widget.existingResponse?.evidenceFileUrl;

    _textController.addListener(_notify);
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  void _notify() {
    widget.onChanged({
      'field_id': widget.field.id,
      'text_response': _textController.text,
      'score': widget.field.isScored ? _scoreValue : null,
      'selected_options': _selectedOptions,
    });
  }

  Future<void> _pickAndUploadEvidence() async {
    if (widget.appraisalId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please save draft first before attaching files.')),
      );
      return;
    }

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
      );

      if (result != null && result.files.single.path != null) {
        final filePath = result.files.single.path!;
        final fileName = result.files.single.name;

        setState(() {
          _isUploadingFile = true;
        });

        final response = await ApiService().uploadMultipart(
          '/appraisals/${widget.appraisalId}/evidence/',
          filePath,
          fields: {'field_id': widget.field.id.toString()},
        );

        if (mounted) {
          setState(() {
            _isUploadingFile = false;
            _evidenceFileUrl = response['evidence_file_url'];
            _uploadedFileName = fileName;
          });

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Evidence "$fileName" uploaded successfully!'),
              backgroundColor: AppConfig.primaryColor,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isUploadingFile = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to upload file: $e'),
            backgroundColor: AppConfig.dangerColor,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final f = widget.field;

    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: context.surfaceColor.withAlpha(120),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: context.textSecondary.withAlpha(30)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  f.label,
                  style: TextStyle(
                    color: context.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              if (f.isRequired)
                const Text(
                  '* Required',
                  style: TextStyle(color: AppConfig.dangerColor, fontSize: 11),
                ),
            ],
          ),
          if (f.description.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              f.description,
              style: TextStyle(color: context.textSecondary, fontSize: 12),
            ),
          ],
          const SizedBox(height: 12),

          if (f.fieldType == 'NARRATIVE') _buildNarrativeInput(context),
          if (f.fieldType == 'SCORE') _buildScoreInput(context),
          if (f.fieldType == 'SCORE_COMMENT') _buildScoreCommentInput(context),
          if (f.fieldType == 'SINGLE_SELECT') _buildSingleSelectInput(context),
          if (f.fieldType == 'MULTI_SELECT') _buildMultiSelectInput(context),

          // ── Evidence / File Attachment Section ──
          const SizedBox(height: 14),
          _buildEvidenceSection(context),
        ],
      ),
    );
  }

  Widget _buildEvidenceSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_evidenceFileUrl != null && _evidenceFileUrl!.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: AppConfig.primaryColor.withAlpha(20),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppConfig.primaryColor.withAlpha(50)),
            ),
            child: Row(
              children: [
                const Icon(Icons.attach_file, color: AppConfig.primaryColor, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _uploadedFileName ?? 'Attached Evidence File',
                    style: const TextStyle(
                      color: AppConfig.primaryColor,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const Icon(Icons.check_circle, color: AppConfig.primaryColor, size: 16),
              ],
            ),
          ),
          const SizedBox(height: 8),
        ],

        if (!widget.readOnly)
          OutlinedButton.icon(
            onPressed: _isUploadingFile ? null : _pickAndUploadEvidence,
            style: OutlinedButton.styleFrom(
              foregroundColor: AppConfig.primaryColor,
              side: BorderSide(color: AppConfig.primaryColor.withAlpha(100)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            ),
            icon: _isUploadingFile
                ? const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppConfig.primaryColor),
                  )
                : const Icon(Icons.upload_file_rounded, size: 18),
            label: Text(
              _isUploadingFile
                  ? 'Uploading...'
                  : (_evidenceFileUrl != null ? 'Replace Attachment' : 'Attach Supporting Document / File'),
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
          ),
      ],
    );
  }

  Widget _buildNarrativeInput(BuildContext context) {
    return TextField(
      controller: _textController,
      enabled: !widget.readOnly,
      maxLines: 4,
      style: TextStyle(color: context.textPrimary, fontSize: 14),
      decoration: InputDecoration(
        hintText: 'Enter details here...',
        hintStyle: TextStyle(color: context.textSecondary.withAlpha(100)),
        filled: true,
        fillColor: context.cardColor,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: context.textSecondary.withAlpha(30)),
        ),
      ),
    );
  }

  Widget _buildScoreInput(BuildContext context) {
    final f = widget.field;
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Score: ${_scoreValue.toStringAsFixed(1)} / ${f.maxScore.toStringAsFixed(0)}',
              style: const TextStyle(
                color: AppConfig.secondaryColor,
                fontWeight: FontWeight.bold,
                fontSize: 15,
              ),
            ),
            Text(
              'Min: ${f.minScore.toStringAsFixed(0)}',
              style: TextStyle(color: context.textSecondary, fontSize: 12),
            ),
          ],
        ),
        if (!widget.readOnly)
          Slider(
            value: _scoreValue,
            min: f.minScore,
            max: f.maxScore,
            divisions: ((f.maxScore - f.minScore) * 2).toInt().clamp(1, 100),
            activeColor: AppConfig.primaryColor,
            inactiveColor: context.textSecondary.withAlpha(40),
            onChanged: (val) {
              setState(() {
                _scoreValue = val;
              });
              _notify();
            },
          ),
      ],
    );
  }

  Widget _buildScoreCommentInput(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildScoreInput(context),
        const SizedBox(height: 10),
        Text(
          'Comments / Justification:',
          style: TextStyle(color: context.textSecondary, fontSize: 12),
        ),
        const SizedBox(height: 6),
        _buildNarrativeInput(context),
      ],
    );
  }

  Widget _buildSingleSelectInput(BuildContext context) {
    final f = widget.field;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: f.options.map((opt) {
        final isSelected = _selectedOptions.contains(opt);
        return ChoiceChip(
          label: Text(opt),
          selected: isSelected,
          selectedColor: AppConfig.primaryColor,
          backgroundColor: context.cardColor,
          labelStyle: TextStyle(
            color: isSelected ? Colors.white : context.textSecondary,
          ),
          onSelected: widget.readOnly
              ? null
              : (selected) {
                  setState(() {
                    _selectedOptions.clear();
                    if (selected) _selectedOptions.add(opt);
                  });
                  _notify();
                },
        );
      }).toList(),
    );
  }

  Widget _buildMultiSelectInput(BuildContext context) {
    final f = widget.field;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: f.options.map((opt) {
        final isSelected = _selectedOptions.contains(opt);
        return FilterChip(
          label: Text(opt),
          selected: isSelected,
          selectedColor: AppConfig.accentColor,
          backgroundColor: context.cardColor,
          labelStyle: TextStyle(
            color: isSelected ? Colors.white : context.textSecondary,
          ),
          onSelected: widget.readOnly
              ? null
              : (selected) {
                  setState(() {
                    if (selected) {
                      _selectedOptions.add(opt);
                    } else {
                      _selectedOptions.remove(opt);
                    }
                  });
                  _notify();
                },
        );
      }).toList(),
    );
  }
}
