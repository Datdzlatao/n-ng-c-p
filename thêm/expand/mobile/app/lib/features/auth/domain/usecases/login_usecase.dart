import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/errors/failures.dart';
import '../entities/user_entity.dart';
import '../repositories/auth_repository.dart';

/// Use Case: Đăng nhập
/// Single Responsibility: chỉ xử lý login logic
class LoginUseCase {
  final AuthRepository repository;
  const LoginUseCase(this.repository);

  Future<Either<Failure, UserEntity>> call(LoginParams params) {
    return repository.login(
      email:    params.email,
      password: params.password,
    );
  }
}

/// Params cho LoginUseCase
class LoginParams extends Equatable {
  final String email;
  final String password;
  const LoginParams({required this.email, required this.password});

  @override
  List<Object> get props => [email, password];
}
