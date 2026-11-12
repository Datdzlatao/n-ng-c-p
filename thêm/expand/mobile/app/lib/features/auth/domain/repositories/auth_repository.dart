import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/user_entity.dart';

/// Interface định nghĩa contract của Auth — Domain layer không biết Firebase
abstract class AuthRepository {
  /// Đăng nhập bằng email/password
  Future<Either<Failure, UserEntity>> login({
    required String email,
    required String password,
  });

  /// Đăng xuất
  Future<Either<Failure, void>> logout();

  /// Lấy thông tin user đang đăng nhập (null nếu chưa đăng nhập)
  Future<Either<Failure, UserEntity?>> getCurrentUser();

  /// Stream theo dõi trạng thái auth realtime
  Stream<UserEntity?> get authStateChanges;
}
