import 'package:flutter/material.dart';
import 'package:camera/camera.dart';

class FaceRegistrationPage extends StatefulWidget {
  final String studentId;
  const FaceRegistrationPage({super.key, required this.studentId});

  @override
  State<FaceRegistrationPage> createState() => _FaceRegistrationPageState();
}

class _FaceRegistrationPageState extends State<FaceRegistrationPage> {
  CameraController? _controller;
  int _progress = 1;

  @override
  void initState() {
    super.initState();
    availableCameras().then((cameras) {
      if (cameras.isNotEmpty) {
        _controller = CameraController(cameras.first, ResolutionPreset.medium);
        _controller!.initialize().then((_) {
          if (!mounted) return;
          setState(() {});
        });
      }
    });
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_controller == null || !_controller!.value.isInitialized) {
      return const Scaffold(backgroundColor: Colors.black, body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: const Text('Đăng Ký Khuôn Mặt', style: TextStyle(color: Colors.white)), backgroundColor: Colors.transparent),
      body: Column(
        children: [
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text('Nhìn thẳng vào camera, đảm bảo đủ ánh sáng', style: TextStyle(color: Colors.white, fontSize: 16)),
          ),
          Expanded(
            child: Center(
              child: ClipOval(
                child: SizedBox(
                  width: 300,
                  height: 350,
                  child: CameraPreview(_controller!),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              children: [
                Text('Chụp $_progress/5', style: const TextStyle(color: Colors.white, fontSize: 20)),
                const SizedBox(height: 20),
                GestureDetector(
                  onTap: () {
                    if (_progress < 5) {
                      setState(() => _progress++);
                    } else {
                      Navigator.pop(context);
                    }
                  },
                  child: Container(
                    width: 80,
                    height: 80,
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(colors: [Color(0xFF6366F1), Color(0xFF06B6D4)]),
                    ),
                    child: const Icon(Icons.camera_alt, color: Colors.white, size: 40),
                  ),
                )
              ],
            ),
          )
        ],
      ),
    );
  }
}
