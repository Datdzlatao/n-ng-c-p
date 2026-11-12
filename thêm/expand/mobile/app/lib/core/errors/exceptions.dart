// Custom exceptions — throw ở Data layer, catch và convert sang Failure ở Repository

/// Lỗi từ API/Firebase response
class ServerException implements Exception {
  final String message;
  const ServerException([this.message = 'Lỗi máy chủ']);
}

/// Lỗi không có cache local
class CacheException implements Exception {
  final String message;
  const CacheException([this.message = 'Không tìm thấy dữ liệu local']);
}

/// Lỗi xác thực Firebase Auth
class AuthException implements Exception {
  final String message;
  const AuthException([this.message = 'Xác thực thất bại']);
}

/// Lỗi nhận diện khuôn mặt
class FaceRecognitionException implements Exception {
  final String message;
  const FaceRecognitionException([this.message = 'Không nhận diện được']);
}

/// Lỗi QR không hợp lệ
class QrException implements Exception {
  final String message;
  const QrException([this.message = 'QR không hợp lệ']);
}

/// Lỗi model AI
class MLException implements Exception {
  final String message;
  const MLException([this.message = 'Lỗi mô hình AI']);
}

/// Lỗi quyền truy cập
class PermissionException implements Exception {
  final String message;
  const PermissionException([this.message = 'Không có quyền']);
}
