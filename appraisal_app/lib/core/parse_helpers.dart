/// Safely converts a JSON value to [double].
///
/// DRF serializes [DecimalField] as strings (e.g. "10.00") to preserve
/// precision. This helper handles both [String] and [num] transparently
/// so Flutter models don't throw "type 'String' is not a subtype of num?".
double? parseDouble(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

/// Safely converts a JSON value to [int].
int? parseInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}
