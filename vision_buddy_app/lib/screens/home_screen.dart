import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'dart:io';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {

  CameraController? _cameraController;
  final FlutterTts _tts = FlutterTts();
  final SpeechToText _stt = SpeechToText();

  bool _cameraOn = true;
  bool _isAnalyzing = false;
  bool _isListening = false;
  bool _sttAvailable = false;
  String _lastDescription = "VisionBuddy is ready. Point camera at anything.";
  String _spokenWords = "";
  String _currentMode = "";

  Timer? _autoTimer;
  static const String BASE_URL = 'http://localhost:8000';

  @override
  void initState() {
    super.initState();
    _initAll();
  }

  Future<void> _initAll() async {
    await _initCamera();
    await _initSTT();
    _startAutoScan();
    await Future.delayed(Duration(seconds: 1));
    await _speak("VisionBuddy ready.");
  }

  // ── TTS ──────────────────────────────────────────────────
  Future<void> _speak(String text) async {
    if (text.trim().isEmpty) return;
    print("SPEAKING: $text");
    try {
      await Process.run('killall', ['say']);
      await Process.run('say', ['-r', '160', text]);
      print("✅ Spoken");
    } catch (e) {
      print("TTS error: $e");
      // fallback to flutter_tts
      try {
        await _tts.setLanguage("en-US");
        await _tts.setVolume(1.0);
        await _tts.setSpeechRate(0.5);
        await _tts.speak(text);
      } catch (e2) {
        print("flutter_tts also failed: $e2");
      }
    }
  }

  // ── STT ──────────────────────────────────────────────────
  Future<void> _initSTT() async {
    _sttAvailable = await _stt.initialize(
      onError: (e) {
        print('STT Error: $e');
        setState(() => _isListening = false);
        if (_cameraOn) _startAutoScan();
      },
      onStatus: (status) {
        print('STT Status: $status');
        if ((status == 'done' || status == 'notListening') && _isListening) {
          _processQuestion();
        }
      },
    );
    print('STT Available: $_sttAvailable');
    setState(() {});
  }

  Future<void> _startListening() async {
    if (!_sttAvailable) {
      await _speak("Microphone not available.");
      return;
    }
    if (_isListening) return;

    _autoTimer?.cancel();
    await Process.run('killall', ['say']);

    setState(() {
      _isListening = true;
      _spokenWords = "";
      _lastDescription = "🎤 Listening... speak now";
    });

    await _stt.listen(
      onResult: (result) {
        setState(() {
          _spokenWords = result.recognizedWords;
          _lastDescription = "🎤 ${result.recognizedWords}";
        });
        if (result.finalResult && result.recognizedWords.isNotEmpty) {
          _processQuestion();
        }
      },
      listenFor: Duration(seconds: 10),
      pauseFor: Duration(seconds: 3),
      partialResults: true,
      localeId: "en_US",
      cancelOnError: false,
    );
  }

  Future<void> _processQuestion() async {
    if (!_isListening) return;
    await _stt.stop();
    setState(() => _isListening = false);

    final question = _spokenWords.trim();
    print("Question heard: $question");

    if (question.isEmpty) {
      setState(() => _lastDescription = "Didn't hear anything. Try again.");
      await _speak("I didn't hear anything. Please try again.");
      if (_cameraOn) _startAutoScan();
      return;
    }

    setState(() => _lastDescription = "You asked: $question");
    await Process.run('say', ['-r', '160', 'Got it.']);
    await Future.delayed(Duration(milliseconds: 800));

    if (_cameraOn && _cameraController?.value.isInitialized == true) {
      await _captureAndAnalyze(force: true, question: question);
    } else {
      await _answerWithoutCamera(question);
    }

    if (_cameraOn) _startAutoScan();
  }

  Future<void> _answerWithoutCamera(String question) async {
    try {
      final response = await http.post(
        Uri.parse('$BASE_URL/question'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'question': question}),
      ).timeout(Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final answer = data['answer'] ?? '';
        if (answer.isNotEmpty) {
          setState(() => _lastDescription = answer);
          await _speak(answer);
        }
      }
    } catch (e) {
      await _speak("Sorry, I couldn't answer that.");
    }
  }

  // ── Camera ────────────────────────────────────────────────
  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) return;
      _cameraController = CameraController(
        cameras.first,
        ResolutionPreset.medium,
        enableAudio: false,
      );
      await _cameraController!.initialize();
      if (mounted) setState(() {});
    } catch (e) {
      print("Camera error: $e");
    }
  }

  Future<void> _toggleCamera() async {
    if (_cameraOn) {
      _stopAutoScan();
      setState(() { _cameraOn = false; _currentMode = ""; });
      await _speak("Camera off.");
    } else {
      setState(() => _cameraOn = true);
      if (_cameraController?.value.isInitialized != true) {
        await _initCamera();
      }
      _startAutoScan();
      await _speak("Camera on.");
    }
  }

  void _startAutoScan() {
    _autoTimer?.cancel();
    _autoTimer = Timer.periodic(Duration(seconds: 4), (_) {
      if (_cameraOn && !_isAnalyzing && !_isListening &&
          _cameraController?.value.isInitialized == true) {
        _captureAndAnalyze(force: false);
      }
    });
  }

  void _stopAutoScan() => _autoTimer?.cancel();

  // ── Core Agent Call ───────────────────────────────────────
  Future<void> _captureAndAnalyze({
    bool force = false,
    String? question,
  }) async {
    if (_isAnalyzing || _cameraController == null || !_cameraOn) return;
    setState(() => _isAnalyzing = true);
    print("📸 Capturing...");

    try {
      final image = await _cameraController!.takePicture();
      final bytes = await image.readAsBytes();
      final base64Image = base64Encode(bytes);
      print("📸 Size: ${bytes.length} bytes");

      final body = {
        'image': base64Image,
        'force': force,
        if (question != null) 'question': question,
      };

      print("📡 Sending...");
      final response = await http.post(
        Uri.parse('$BASE_URL/analyze'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      ).timeout(Duration(seconds: 30));

      print("📡 Status: ${response.statusCode}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final description = data['description'] ?? '';
        final shouldSpeak = data['should_speak'] ?? false;
        final modeUsed = data['mode_used'] ?? '';

        print("🗣️ shouldSpeak: $shouldSpeak | desc: $description");

        if ((shouldSpeak || force) && description.isNotEmpty) {
          setState(() {
            _lastDescription = description;
            _currentMode = modeUsed;
          });
          await Future.delayed(Duration(milliseconds: 200));
          await _speak(description);
        }
      } else {
        print("❌ Backend error: ${response.statusCode}");
        if (force) {
          setState(() => _lastDescription = "Backend error. Try again.");
        }
      }

    } on TimeoutException {
      print("❌ TIMEOUT");
      if (force) {
        setState(() => _lastDescription = "Timeout. Is backend running?");
        await _speak("Taking too long. Please try again.");
      }
    } catch (e) {
      print("❌ Error: $e");
      if (force) {
        setState(() => _lastDescription = "Error: $e");
      }
    } finally {
      setState(() => _isAnalyzing = false);
    }
  }

  // ── UI ────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(children: [

          // Header
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(children: [
                  Icon(Icons.visibility, color: Colors.green, size: 28),
                  SizedBox(width: 8),
                  Text("VisionBuddy",
                    style: TextStyle(color: Colors.white,
                      fontSize: 22, fontWeight: FontWeight.bold)),
                ]),
                GestureDetector(
                  onTap: _toggleCamera,
                  child: Container(
                    padding: EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      color: _cameraOn ? Colors.green : Colors.red,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(children: [
                      Icon(
                        _cameraOn ? Icons.videocam : Icons.videocam_off,
                        color: Colors.white, size: 18),
                      SizedBox(width: 6),
                      Text(_cameraOn ? "CAM ON" : "CAM OFF",
                        style: TextStyle(color: Colors.white,
                          fontWeight: FontWeight.bold, fontSize: 13)),
                    ]),
                  ),
                ),
              ],
            ),
          ),

          // Camera preview
          Expanded(
            flex: 5,
            child: Container(
              margin: EdgeInsets.symmetric(horizontal: 8),
              child: _cameraOn && _cameraController?.value.isInitialized == true
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Stack(children: [
                      CameraPreview(_cameraController!),

                      // Live / Analyzing badge
                      Positioned(top: 12, left: 12,
                        child: Container(
                          padding: EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: Colors.black54,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Row(children: [
                            Container(
                              width: 8, height: 8,
                              decoration: BoxDecoration(
                                color: _isAnalyzing
                                  ? Colors.orange : Colors.green,
                                shape: BoxShape.circle,
                              ),
                            ),
                            SizedBox(width: 6),
                            Text(
                              _isAnalyzing ? "Analyzing..." : "Live",
                              style: TextStyle(
                                color: Colors.white, fontSize: 12)),
                          ]),
                        ),
                      ),

                      // Mode badge
                      if (_currentMode.isNotEmpty)
                        Positioned(top: 12, right: 12,
                          child: Container(
                            padding: EdgeInsets.symmetric(
                              horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              color: _modeColor(_currentMode),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(_modeEmoji(_currentMode),
                              style: TextStyle(color: Colors.white,
                                fontSize: 12, fontWeight: FontWeight.bold)),
                          ),
                        ),
                    ]),
                  )
                : Container(
                    decoration: BoxDecoration(
                      color: Colors.grey[900],
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.videocam_off,
                          color: Colors.grey, size: 64),
                        SizedBox(height: 12),
                        Text("Camera Off",
                          style: TextStyle(color: Colors.grey, fontSize: 20)),
                        SizedBox(height: 8),
                        Text("Mic still works for questions",
                          style: TextStyle(
                            color: Colors.grey[600], fontSize: 14)),
                      ],
                    ),
                  ),
            ),
          ),

          SizedBox(height: 10),

          // Description box — BIG visible text
          Container(
            margin: EdgeInsets.symmetric(horizontal: 16),
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _isListening ? Colors.blue : Colors.green,
                width: 2,
              ),
            ),
            child: Row(children: [
              Expanded(
                child: Text(
                  _isListening
                    ? "🎤 ${_spokenWords.isEmpty
                        ? 'Listening...' : _spokenWords}"
                    : _lastDescription,
                  style: TextStyle(
                    color: _isListening ? Colors.blue[300] : Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    height: 1.5,
                  ),
                  maxLines: 5,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              SizedBox(width: 8),
              IconButton(
                icon: Icon(Icons.volume_up, color: Colors.green, size: 24),
                onPressed: () => _speak(_lastDescription),
              ),
            ]),
          ),

          SizedBox(height: 12),

          // Bottom buttons
          Padding(
            padding: EdgeInsets.only(bottom: 24),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [

                // Replay last description
                _circleBtn(
                  icon: Icons.replay,
                  color: Colors.grey[800]!,
                  size: 60,
                  onTap: () => _speak(_lastDescription),
                  label: "Replay",
                ),

                // Mic button — tap to ask
                GestureDetector(
                  onTap: _isListening ? _processQuestion : _startListening,
                  child: Container(
                    width: 85, height: 85,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _isListening ? Colors.red : Colors.blue,
                      boxShadow: [BoxShadow(
                        color: (_isListening ? Colors.red : Colors.blue)
                          .withOpacity(0.5),
                        blurRadius: 20, spreadRadius: 5,
                      )],
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          _isListening ? Icons.stop : Icons.mic,
                          color: Colors.white, size: 34),
                        SizedBox(height: 2),
                        Text(
                          _isListening ? "Send" : "Ask",
                          style: TextStyle(
                            color: Colors.white, fontSize: 11)),
                      ],
                    ),
                  ),
                ),

                // Manual scan
                _circleBtn(
                  icon: Icons.camera_alt,
                  color: Colors.green,
                  size: 60,
                  onTap: () => _captureAndAnalyze(force: true),
                  label: "Scan",
                ),

              ],
            ),
          ),

        ]),
      ),
    );
  }

  // ── Helpers ───────────────────────────────────────────────
  Color _modeColor(String mode) {
    switch (mode) {
      case 'medicine':   return Colors.red.withOpacity(0.85);
      case 'navigation': return Colors.green.withOpacity(0.85);
      case 'text':       return Colors.orange.withOpacity(0.85);
      case 'money':      return Colors.purple.withOpacity(0.85);
      default:           return Colors.blue.withOpacity(0.85);
    }
  }

  String _modeEmoji(String mode) {
    switch (mode) {
      case 'medicine':   return '💊 Medicine';
      case 'navigation': return '🚶 Navigate';
      case 'text':       return '📄 Text';
      case 'money':      return '💵 Money';
      default:           return '🌍 General';
    }
  }

  Widget _circleBtn({
    required IconData icon,
    required Color color,
    required double size,
    required VoidCallback onTap,
    String label = "",
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Column(children: [
        Container(
          width: size, height: size,
          decoration: BoxDecoration(
            color: color, shape: BoxShape.circle),
          child: Icon(icon, color: Colors.white, size: size * 0.42),
        ),
        if (label.isNotEmpty) ...[
          SizedBox(height: 4),
          Text(label, style: TextStyle(color: Colors.grey, fontSize: 11)),
        ]
      ]),
    );
  }

  @override
  void dispose() {
    _autoTimer?.cancel();
    _cameraController?.dispose();
    _tts.stop();
    _stt.stop();
    super.dispose();
  }
}