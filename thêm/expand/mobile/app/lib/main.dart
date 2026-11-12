// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  MAIN.DART — Entry point của Smart Attendance App                        ║
// ║  Thứ tự khởi tạo: Flutter binding → Firebase → DI → App               ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app.dart';
import 'firebase_options.dart';
import 'injection_container.dart' as di;

void main() async {
  // Đảm bảo Flutter binding được khởi tạo trước khi gọi bất kỳ native API nào
  WidgetsFlutterBinding.ensureInitialized();

  // Khóa màn hình theo chiều dọc (portrait) — phù hợp app di động
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Thiết lập style thanh trạng thái (status bar)
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
    ),
  );

  // Khởi tạo Firebase — phải chạy trước khi dùng bất kỳ Firebase service nào
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  // Khởi tạo tất cả dependencies (GetIt service locator)
  await di.init();

  // Chạy ứng dụng
  runApp(const SmartAttendanceApp());
}
