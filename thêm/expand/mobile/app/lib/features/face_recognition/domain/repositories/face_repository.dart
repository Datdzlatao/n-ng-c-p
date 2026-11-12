import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/face_data_entity.dart';
import 'package:image/image.dart' as img;

abstract class FaceRepository {
  /// Đăng ký khuôn mặt cho học sinh (Admin/Teacher thực hiện)
  Future<Either<Failure, void>> registerFace({
    required String studentId,
    required img.Image faceImage,
  });

  /// Xác minh khuôn mặt so với database
  Future<Either<Failure, FaceVerificationResult>> verifyFace({
    required img.Image faceImage,
    required String classId, // Chỉ so sánh trong cùng lớp để tăng tốc
  });

  /// Lấy embedding của một học sinh
  Future<Either<Failure, FaceDataEntity?>> getFaceData(String studentId);

  /// Xóa khuôn mặt (Admin only)
  Future<Either<Failure, void>> deleteFaceData(String studentId);
}
