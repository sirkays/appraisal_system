import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'config.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  String? _token;
  String? _baseUrlOverride;

  Future<String> get baseUrl async {
    if (_baseUrlOverride != null && _baseUrlOverride!.isNotEmpty) {
      return _baseUrlOverride!;
    }
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('api_base_url');
    if (saved != null && saved.isNotEmpty) {
      _baseUrlOverride = saved;
      return saved;
    }
    return AppConfig.defaultBaseUrl;
  }

  Future<void> setBaseUrl(String url) async {
    _baseUrlOverride = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_base_url', url);
  }

  void clearBaseUrlCache() {
    _baseUrlOverride = null;
  }

  Future<String?> get token async {
    if (_token != null) return _token;
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('auth_token');
    return _token;
  }

  Future<void> setToken(String? token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    if (token == null) {
      await prefs.remove('auth_token');
    } else {
      await prefs.setString('auth_token', token);
    }
  }

  Future<Map<String, String>> _headers() async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    final authToken = await token;
    if (authToken != null && authToken.isNotEmpty) {
      headers['Authorization'] = 'Token $authToken';
    }
    return headers;
  }

  Future<dynamic> get(String endpoint) async {
    final base = await baseUrl;
    final url = Uri.parse('$base$endpoint');
    final response = await http.get(url, headers: await _headers());
    return _processResponse(response);
  }

  Future<dynamic> post(String endpoint, Map<String, dynamic> body) async {
    final base = await baseUrl;
    final url = Uri.parse('$base$endpoint');
    final response = await http.post(
      url,
      headers: await _headers(),
      body: jsonEncode(body),
    );
    return _processResponse(response);
  }

  Future<dynamic> patch(String endpoint, Map<String, dynamic> body) async {
    final base = await baseUrl;
    final url = Uri.parse('$base$endpoint');
    final response = await http.patch(
      url,
      headers: await _headers(),
      body: jsonEncode(body),
    );
    return _processResponse(response);
  }

  Future<dynamic> uploadMultipart(
    String endpoint,
    String filePath, {
    String fieldName = 'file',
    Map<String, String>? fields,
  }) async {
    final base = await baseUrl;
    final url = Uri.parse('$base$endpoint');
    final request = http.MultipartRequest('POST', url);

    final authToken = await token;
    if (authToken != null && authToken.isNotEmpty) {
      request.headers['Authorization'] = 'Token $authToken';
    }

    if (fields != null) {
      request.fields.addAll(fields);
    }

    final file = await http.MultipartFile.fromPath(fieldName, filePath);
    request.files.add(file);

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    return _processResponse(response);
  }

  dynamic _processResponse(http.Response response) {
    final statusCode = response.statusCode;
    final body = response.body.isNotEmpty ? jsonDecode(response.body) : null;

    if (statusCode >= 200 && statusCode < 300) {
      return body;
    } else if (statusCode == 401) {
      setToken(null);
      throw Exception('Session expired or unauthorized. Please log in again.');
    } else {
      final errorMsg = (body is Map && body.containsKey('error'))
          ? body['error']
          : (body is Map && body.containsKey('detail'))
              ? body['detail']
              : 'Request failed with status $statusCode';
      throw Exception(errorMsg);
    }
  }
}
