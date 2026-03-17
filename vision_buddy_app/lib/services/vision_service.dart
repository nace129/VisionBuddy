import 'dart:convert';
import 'package:http/http.dart' as http;

class VisionService {
  // ✅ Flutter web = localhost | Android phone = your laptop IP
  static String baseUrl = 'http://localhost:8000';

  /// Main agent call — Nemotron decides mode automatically
  static Future<Map<String, dynamic>> analyzeFrame({
    required String base64Image,
    String? userQuestion,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/analyze'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'image': base64Image,
          'mode': 'auto',            // Nemotron decides mode!
          if (userQuestion != null) 
            'user_question': userQuestion,
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return {
        'response': 'Analysis failed. Backend returned ${response.statusCode}.',
        'should_speak': true
      };
    } on Exception catch (e) {
      return {
        'response': 'Connection error. Is backend running on port 8000?',
        'should_speak': false,
        'action_taken': 'error'
      };
    }
  }

static Future<String> analyzeImage({
  required String base64Image,
  String mode = 'general',
}) async {
  try {
    print('📤 Sending image to backend, size: ${base64Image.length}');
    print('🌐 URL: $baseUrl/analyze');

    final response = await http.post(
      Uri.parse('$baseUrl/analyze'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'image': base64Image,
        'mode': mode,
      }),
    ).timeout(Duration(seconds: 30));

    print('📥 Response status: ${response.statusCode}');
    print('📥 Response body: ${response.body}');  // ← ADD

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      print('✅ Description: ${data['description']}');
      return data['description'];
    } else {
      print('❌ Error response: ${response.body}');
      return 'Server error ${response.statusCode}. Please try again.';
    }
  } catch (e) {
    print('❌ Connection error: $e');
    return 'Connection error: $e';
  }
}
  /// Follow-up question — uses memory, no image needed
  static Future<Map<String, dynamic>> askQuestion(String question) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/question'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'question': question}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) return jsonDecode(response.body);
      return {'response': 'Could not answer. Try again.', 'should_speak': true};
    } catch (_) {
      return {'response': 'Connection error.', 'should_speak': true};
    }
  }

  static Future<bool> checkHealth() async {
    try {
      final r = await http.get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 4));
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
// import 'dart:convert';
// import 'package:http/http.dart' as http;

// class VisionService {
//   // ⚠️ CHANGE THIS to your laptop IP at hackathon
//   // Run: ipconfig (Windows) or ifconfig (Mac) to find it
//   static const String baseUrl = 'http://localhost:8000';

//   static Future<String> analyzeImage({
//     required String base64Image,
//     String mode = 'general',
//   }) async {
//     try {
//       final response = await http.post(
//         Uri.parse('$baseUrl/analyze'),
//         headers: {'Content-Type': 'application/json'},
//         body: jsonEncode({
//           'image': base64Image,
//           'mode': mode,
//         }),
//       ).timeout(Duration(seconds: 15));

//       if (response.statusCode == 200) {
//         final data = jsonDecode(response.body);
//         return data['description'];
//       } else {
//         return 'Sorry, I could not analyze the image. Please try again.';
//       }
//     } catch (e) {
//       return 'Connection error. Please check your internet connection.';
//     }
//   }
// }