import '../core/parse_helpers.dart';

class FormFieldModel {
  final int id;
  final String label;
  final String description;
  final String fieldType; // NARRATIVE, SCORE, SCORE_COMMENT, SINGLE_SELECT, MULTI_SELECT
  final String filledBy;  // APPRAISEE, SUPERVISOR, HOD, DIRECTORATE
  final double maxScore;
  final double minScore;
  final List<String> options;
  final bool reviewerCanScore;
  final String? reviewerScoreRole;
  final double? reviewerScoreMax;
  final bool reviewerCanComment;
  final String? reviewerCommentRole;
  final bool isRequired;
  final int order;

  FormFieldModel({
    required this.id,
    required this.label,
    required this.description,
    required this.fieldType,
    required this.filledBy,
    required this.maxScore,
    required this.minScore,
    required this.options,
    required this.reviewerCanScore,
    this.reviewerScoreRole,
    this.reviewerScoreMax,
    required this.reviewerCanComment,
    this.reviewerCommentRole,
    required this.isRequired,
    required this.order,
  });

  factory FormFieldModel.fromJson(Map<String, dynamic> json) {
    return FormFieldModel(
      id: json['id'],
      label: json['label'] ?? '',
      description: json['description'] ?? '',
      fieldType: json['field_type'] ?? 'NARRATIVE',
      filledBy: json['filled_by'] ?? 'APPRAISEE',
      // DRF DecimalField comes as String — use parseDouble() to handle both
      maxScore: parseDouble(json['max_score']) ?? 10.0,
      minScore: parseDouble(json['min_score']) ?? 0.0,
      options: (json['options'] as List?)?.map((e) => e.toString()).toList() ?? [],
      reviewerCanScore: json['reviewer_can_score'] ?? false,
      reviewerScoreRole: json['reviewer_score_role'],
      reviewerScoreMax: parseDouble(json['reviewer_score_max']),
      reviewerCanComment: json['reviewer_can_comment'] ?? false,
      reviewerCommentRole: json['reviewer_comment_role'],
      isRequired: json['is_required'] ?? true,
      order: json['order'] ?? 0,
    );
  }

  bool get isScored => fieldType == 'SCORE' || fieldType == 'SCORE_COMMENT';
}

class FormSectionModel {
  final int id;
  final String name;
  final String description;
  final double sectionWeight;
  final int order;
  final List<FormFieldModel> fields;

  FormSectionModel({
    required this.id,
    required this.name,
    required this.description,
    required this.sectionWeight,
    required this.order,
    required this.fields,
  });

  factory FormSectionModel.fromJson(Map<String, dynamic> json) {
    return FormSectionModel(
      id: json['id'],
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      // DRF DecimalField — comes as String
      sectionWeight: parseDouble(json['section_weight']) ?? 0.0,
      order: json['order'] ?? 0,
      fields: (json['fields'] as List?)
              ?.map((e) => FormFieldModel.fromJson(e))
              .toList() ??
          [],
    );
  }
}

class FormFieldResponseModel {
  final int id;
  final int fieldId;
  final int? respondedBy;
  final String? respondedByName;
  final String responseType; // PRIMARY, REVIEWER_SCORE, REVIEWER_COMMENT
  final String textResponse;
  final double? score;
  final List<String> selectedOptions;
  final String? evidenceFileUrl;
  final String? respondedAt;

  FormFieldResponseModel({
    required this.id,
    required this.fieldId,
    this.respondedBy,
    this.respondedByName,
    required this.responseType,
    required this.textResponse,
    this.score,
    required this.selectedOptions,
    this.evidenceFileUrl,
    this.respondedAt,
  });

  factory FormFieldResponseModel.fromJson(Map<String, dynamic> json) {
    return FormFieldResponseModel(
      id: json['id'],
      fieldId: json['field_id'],
      respondedBy: json['responded_by'],
      respondedByName: json['responded_by_name'],
      responseType: json['response_type'] ?? 'PRIMARY',
      textResponse: json['text_response'] ?? '',
      // DRF DecimalField — comes as String
      score: parseDouble(json['score']),
      selectedOptions: (json['selected_options'] as List?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      evidenceFileUrl: json['evidence_file_url'],
      respondedAt: json['responded_at'],
    );
  }
}
