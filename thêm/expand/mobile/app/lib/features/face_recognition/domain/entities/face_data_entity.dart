import 'package:equatable/equatable.dart';

/// Kết quả nhận diện khuôn mặt
class FaceDataEntity extends Equatable {
  final String studentId;       // Mã học sinh
  final List<double> embedding; // Vector 128-d của khuôn mặt (từ TFLite)
  final DateTime registeredAt;  // Thời điểm đăng ký

  const FaceDataEntity({
    required this.studentId,
    required this.embedding,
    required this.registeredAt,
  });

  @override
  List<Object> get props => [studentId, embedding, registeredAt];
}

/// Kết quả xác minh khuôn mặt
class FaceVerificationResult extends Equatable {
  final bool isMatch;           // Có khớp không
  final String? studentId;      // Mã học sinh nếu match
  final String? studentName;    // Tên học sinh nếu match
  final double confidence;      // Độ tương đồng (0.0 - 1.0)

  const FaceVerificationResult({
    required this.isMatch,
    this.studentId,
    this.studentName,
    required this.confidence,
  });

  @override
  List<Object?> get props => [isMatch, studentId, studentName, confidence];
}
