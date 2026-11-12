import 'package:equatable/equatable.dart';

enum AttendanceMethod { qrCode, faceId }
enum AttendanceStatus { present, late, absent }

class AttendanceEntity extends Equatable {
  final String id;
  final String studentId;
  final String studentName;
  final String sessionId;
  final String classId;
  final DateTime timestamp;
  final AttendanceMethod method;
  final AttendanceStatus status;
  final bool dressCodePassed;  // Kết quả kiểm tra trang phục
  final bool isSynced;         // Đã đồng bộ lên server chưa (offline support)

  const AttendanceEntity({
    required this.id,
    required this.studentId,
    required this.studentName,
    required this.sessionId,
    required this.classId,
    required this.timestamp,
    required this.method,
    required this.status,
    this.dressCodePassed = true,
    this.isSynced = false,
  });

  @override
  List<Object> get props => [
    id, studentId, studentName, sessionId, classId,
    timestamp, method, status, dressCodePassed, isSynced,
  ];
}
