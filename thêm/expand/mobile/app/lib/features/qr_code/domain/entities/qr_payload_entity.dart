import 'package:equatable/equatable.dart';

/// Dữ liệu được mã hóa trong QR Code
class QrPayloadEntity extends Equatable {
  final String sessionId;    // ID phiên điểm danh
  final String teacherId;    // ID giáo viên tạo QR
  final String classId;      // Lớp học
  final DateTime createdAt;  // Thời điểm tạo (dùng kiểm tra TTL)
  final String nonce;        // Giá trị ngẫu nhiên — chống replay attack
  final String signature;    // HMAC-SHA256 signature

  const QrPayloadEntity({
    required this.sessionId,
    required this.teacherId,
    required this.classId,
    required this.createdAt,
    required this.nonce,
    required this.signature,
  });

  @override
  List<Object> get props => [sessionId, teacherId, classId, createdAt, nonce, signature];
}
