// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  APP.DART — Root Widget & Router Configuration                           ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import 'core/theme/app_theme.dart';
import 'features/auth/presentation/bloc/auth_bloc.dart';
import 'features/auth/presentation/pages/login_page.dart';
import 'features/auth/presentation/pages/splash_page.dart';
import 'features/attendance/presentation/pages/attendance_home_page.dart';
import 'features/qr_code/presentation/pages/qr_scanner_page.dart';
import 'features/qr_code/presentation/pages/qr_display_page.dart';
import 'features/face_recognition/presentation/pages/face_attendance_page.dart';
import 'features/face_recognition/presentation/pages/face_registration_page.dart';
import 'features/dashboard/presentation/pages/admin_dashboard_page.dart';
import 'features/dashboard/presentation/pages/teacher_dashboard_page.dart';
import 'features/report/presentation/pages/report_page.dart';
import 'injection_container.dart' as di;

class SmartAttendanceApp extends StatelessWidget {
  const SmartAttendanceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      // Cung cấp AuthBloc cho toàn bộ widget tree
      providers: [
        BlocProvider<AuthBloc>(
          create: (_) => di.sl<AuthBloc>()..add(AppStarted()),
        ),
      ],
      child: MaterialApp.router(
        title: 'Điểm Danh STEM',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,       // Sử dụng dark theme premium
        routerConfig: _router,
      ),
    );
  }
}

// ── GoRouter: Định nghĩa tất cả routes ────────────────────────────────────
final GoRouter _router = GoRouter(
  initialLocation: '/splash',
  // Redirect logic dựa trên trạng thái auth
  redirect: (BuildContext context, GoRouterState state) {
    // Xem xét trạng thái auth từ BLoC ở đây nếu cần
    return null;
  },
  routes: [
    // Splash screen — kiểm tra auth state khi khởi động
    GoRoute(
      path: '/splash',
      name: 'splash',
      builder: (context, state) => const SplashPage(),
    ),

    // Login screen
    GoRoute(
      path: '/login',
      name: 'login',
      builder: (context, state) => const LoginPage(),
    ),

    // ── Student Routes ──────────────────────────────────────────────────────
    GoRoute(
      path: '/home',
      name: 'home',
      builder: (context, state) => const AttendanceHomePage(),
    ),
    GoRoute(
      path: '/qr-scan',
      name: 'qr-scan',
      builder: (context, state) => const QrScannerPage(),
    ),
    GoRoute(
      path: '/face-attendance',
      name: 'face-attendance',
      builder: (context, state) => const FaceAttendancePage(),
    ),

    // ── Teacher Routes ──────────────────────────────────────────────────────
    GoRoute(
      path: '/teacher-dashboard',
      name: 'teacher-dashboard',
      builder: (context, state) => const TeacherDashboardPage(),
    ),
    GoRoute(
      path: '/qr-display',
      name: 'qr-display',
      builder: (context, state) {
        // Nhận sessionId từ query params
        final sessionId = state.uri.queryParameters['sessionId'] ?? '';
        return QrDisplayPage(sessionId: sessionId);
      },
    ),
    GoRoute(
      path: '/face-register',
      name: 'face-register',
      builder: (context, state) {
        final studentId = state.uri.queryParameters['studentId'] ?? '';
        return FaceRegistrationPage(studentId: studentId);
      },
    ),

    // ── Admin Routes ────────────────────────────────────────────────────────
    GoRoute(
      path: '/admin-dashboard',
      name: 'admin-dashboard',
      builder: (context, state) => const AdminDashboardPage(),
    ),
    GoRoute(
      path: '/report',
      name: 'report',
      builder: (context, state) => const ReportPage(),
    ),
  ],
  // Custom error page khi route không tồn tại
  errorBuilder: (context, state) => Scaffold(
    body: Center(
      child: Text(
        'Trang không tồn tại: ${state.error}',
        style: const TextStyle(color: Colors.white),
      ),
    ),
  ),
);
