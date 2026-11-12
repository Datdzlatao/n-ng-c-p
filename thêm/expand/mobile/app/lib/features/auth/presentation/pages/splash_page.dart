import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';

// Mocks
class User { final String role; User({required this.role}); }
class UserRole { static const String student = 'student'; static const String teacher = 'teacher'; static const String admin = 'admin'; }
abstract class AuthState {}
class Authenticated extends AuthState { final User user; Authenticated(this.user); }
class Unauthenticated extends AuthState {}
class AuthLoading extends AuthState {}
class AuthBloc extends Bloc<dynamic, AuthState> { AuthBloc() : super(AuthLoading()); }

class SplashPage extends StatelessWidget {
  const SplashPage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocListener<AuthBloc, AuthState>(
      listener: (context, state) {
        if (state is Authenticated) {
          if (state.user.role == UserRole.teacher) {
            context.go('/teacher-dashboard');
          } else if (state.user.role == UserRole.admin) {
            context.go('/admin-dashboard');
          } else {
            context.go('/home');
          }
        } else if (state is Unauthenticated) {
          context.go('/login');
        }
      },
      child: Scaffold(
        body: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF0F0F1A), Color(0xFF1A1A2E)],
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
            ),
          ),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.school,
                  size: 100,
                  color: Colors.white,
                )
                .animate(onPlay: (controller) => controller.repeat())
                .shimmer(duration: 1200.ms, color: const Color(0xFF6366F1))
                .scale(begin: const Offset(0.8, 0.8), end: const Offset(1.0, 1.0)),
                const SizedBox(height: 24),
                const Text(
                  'Điểm Danh STEM',
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Hệ Thống Điểm Danh Thông Minh',
                  style: TextStyle(
                    fontSize: 16,
                    color: Color(0xFF94A3B8),
                  ),
                ),
                const SizedBox(height: 48),
                const CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF6366F1)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
