
import 'package:flutter_tts/flutter_tts.dart';

class TtsService {
  static final FlutterTts _tts = FlutterTts();
  static bool _initialized = false;
  static bool isSpeaking = false;        // ← ADD THIS LINE

  static Future<void> init() async {
    if (_initialized) return;
    await _tts.setLanguage("en-US");
    await _tts.setSpeechRate(0.45);
    await _tts.setVolume(1.0);
    await _tts.setPitch(1.0);

    // Track speaking state automatically
    _tts.setStartHandler(() => isSpeaking = true);     // ← ADD
    _tts.setCompletionHandler(() => isSpeaking = false); // ← ADD
    _tts.setCancelHandler(() => isSpeaking = false);    // ← ADD

    _initialized = true;
  }

  static Future<void> speak(String text) async {
    await init();
    await _tts.stop();
    await _tts.speak(text);
  }

  static Future<void> stop() async {
    await _tts.stop();
    isSpeaking = false;
  }
}// import 'package:flutter_tts/flutter_tts.dart';

// class TtsService {
//   static final FlutterTts _tts = FlutterTts();
//   static bool _initialized = false;

//   static Future<void> init() async {
//     if (_initialized) return;
//     await _tts.setLanguage("en-US");
//     await _tts.setSpeechRate(0.45);  // Slightly slow = easier to understand
//     await _tts.setVolume(1.0);
//     await _tts.setPitch(1.0);
//     _initialized = true;
//   }

//   static Future<void> speak(String text) async {
//     await init();
//     await _tts.stop();  // Stop if already speaking
//     await _tts.speak(text);
//   }

//   static Future<void> stop() async {
//     await _tts.stop();
//   }
// }