import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:flutter_animate/flutter_animate.dart';

class QrDisplayPage extends StatefulWidget {
  const QrDisplayPage({super.key});

  @override
  State<QrDisplayPage> createState() => _QrDisplayPageState();
}

class _QrDisplayPageState extends State<QrDisplayPage> {
  int secondsRemaining = 60;
  bool isExpired = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Mã QR Điểm Danh', style: TextStyle(color: Colors.white)),
        actions: [
          IconButton(
            icon: const Icon(Icons.close, color: Colors.white),
            onPressed: () => Navigator.of(context).pop(),
          )
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.symmetric(horizontal: 24),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Column(
                children: [
                  Text('Lớp 10A1 - Môn Toán', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                  SizedBox(height: 8),
                  Text('Bắt đầu: 08:00 AM', style: TextStyle(color: Colors.grey, fontSize: 16)),
                ],
              ),
            ),
            const SizedBox(height: 40),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF9333EA).withOpacity(0.5),
                    blurRadius: 40,
                    spreadRadius: 10,
                  )
                ],
              ),
              padding: const EdgeInsets.all(16),
              child: QrImageView(
                data: 'https://example.com/attendance/xyz',
                version: QrVersions.auto,
                size: 250.0,
              ),
            ).animate(onPlay: (c) => c.repeat(reverse: true)).scale(duration: 2.seconds, begin: const Offset(1,1), end: const Offset(1.05, 1.05)),
            const SizedBox(height: 40),
            Text(
              'Làm mới sau: $secondsRemaining s',
              style: const TextStyle(color: Colors.white, fontSize: 18),
            ),
            const SizedBox(height: 16),
            if (isExpired)
              ElevatedButton(
                onPressed: () {
                  setState(() {
                    secondsRemaining = 60;
                    isExpired = false;
                  });
                },
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6366F1)),
                child: const Text('Làm mới QR', style: TextStyle(color: Colors.white)),
              ),
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.green,
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Text(
                'Đã điểm danh: 12/40',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
