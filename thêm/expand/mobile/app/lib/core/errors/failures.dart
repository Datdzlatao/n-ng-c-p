// Failure classes dùng với Either<Failure, T> pattern trong Clean Architecture
import 'package:equatable/equatable.dart';

/// Base class cho tất cả failures
abstract class Failure extends Equatable {
  final String message;
  const Failure(this.message);
  @override
  List<Object> get props => [message];
}

/// Lỗi kết nối mạng
class NetworkFailure extends Failure {
  const NetworkFailure([super.message = 'Không có kết nối mạng']);
}

/// Lỗi từ Firebase / Server
class ServerFailure extends Failure {
  const ServerFailure([super.message = 'Lỗi máy chủ']);
}

/// Lỗi xác thực (sai mật khẩu, tài khoản bị khóa...)
class AuthFailure extends Failure {
  const AuthFailure([super.message = 'Xác thực thất bại']);
}

/// Lỗi cache / local storage
class CacheFailure extends Failure {
  const CacheFailure([super.message = 'Lỗi lưu trữ cục bộ']);
}

/// Lỗi nhận diện khuôn mặt
class FaceRecognitionFailure extends Failure {
  const FaceRecognitionFailure([super.message = 'Không nhận diện được khuôn mặt']);
}

/// Lỗi QR Code không hợp lệ hoặc hết hạn
class QrFailure extends Failure {
  const QrFailure([super.message = 'Mã QR không hợp lệ hoặc đã hết hạn']);
}

/// Lỗi model TFLite (dress code / face embedding)
class MLFailure extends Failure {
  const MLFailure([super.message = 'Lỗi xử lý AI']);
}

/// Lỗi quyền truy cập (camera, storage)
class PermissionFailure extends Failure {
  const PermissionFailure([super.message = 'Không có quyền truy cập']);
}
