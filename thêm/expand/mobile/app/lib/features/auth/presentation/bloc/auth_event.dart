import 'package:equatable/equatable.dart';

abstract class AuthEvent extends Equatable {
  const AuthEvent();
  @override
  List<Object?> get props => [];
}

/// App vừa khởi động — kiểm tra xem user đã đăng nhập chưa
class AppStarted extends AuthEvent {}

/// User nhấn nút Đăng nhập
class LoginRequested extends AuthEvent {
  final String email;
  final String password;
  const LoginRequested({required this.email, required this.password});
  @override
  List<Object> get props => [email, password];
}

/// User nhấn nút Đăng xuất
class LogoutRequested extends AuthEvent {}
