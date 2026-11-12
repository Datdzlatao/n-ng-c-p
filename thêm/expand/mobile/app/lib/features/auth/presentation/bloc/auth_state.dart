import 'package:equatable/equatable.dart';
import '../../domain/entities/user_entity.dart';

abstract class AuthState extends Equatable {
  const AuthState();
  @override
  List<Object?> get props => [];
}

/// Đang kiểm tra trạng thái auth (splash screen)
class AuthInitial extends AuthState {}

/// Đang xử lý (loading)
class AuthLoading extends AuthState {}

/// Đã đăng nhập thành công
class Authenticated extends AuthState {
  final UserEntity user;
  const Authenticated(this.user);
  @override
  List<Object> get props => [user];
}

/// Chưa đăng nhập
class Unauthenticated extends AuthState {}

/// Đăng nhập thất bại
class AuthError extends AuthState {
  final String message;
  const AuthError(this.message);
  @override
  List<Object> get props => [message];
}
