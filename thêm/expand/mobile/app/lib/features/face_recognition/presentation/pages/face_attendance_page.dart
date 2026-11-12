import 'package:flutter/material.dart';
import 'package:camera/camera.dart';

class FaceAttendancePage extends StatefulWidget {
  const FaceAttendancePage({super.key});

  @override
  State<FaceAttendancePage> createState() => _FaceAttendancePageState();
}

class _FaceAttendancePageState extends State<FaceAttendancePage> {
  CameraController? _controller;
  bool _isSuccess = false;

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
      body: Stack(
        fit: StackFit.expand,
        children: [
          CameraPreview(_controller!),
          // Overlay
          if (_isSuccess)
            Container(color: Colors.green.withOpacity(0.5))
          else
            CustomPaint(painter: FaceDetectionPainter()),
            
          const Positioned(
            top: 60,
            left: 0,
            right: 0,
            child: Center(
              child: Text(
                'Đang tìm khuôn mặt...',
                style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold, backgroundColor: Colors.black54),
              ),
            ),
          ),
          const Positioned(
            top: 60,
            right: 20,
            child: Icon(Icons.check_circle, color: Colors.green, size: 30),
          )
        ],
      ),
    );
  }
}

class FaceDetectionPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.blue
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;
    
    final rect = Rect.fromCenter(center: Offset(size.width/2, size.height/2), width: 250, height: 350);
    canvas.drawRect(rect, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
