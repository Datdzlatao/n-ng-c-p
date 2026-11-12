import 'package:equatable/equatable.dart';

/// Enum phân quyền người dùng
enum UserRole { student, teacher, admin }

/// Entity người dùng — pure Dart, không phụ thuộc Firebase
class UserEntity extends Equatable {
  final String id;          // Firebase UID
  final String email;
  final String fullName;    // Họ tên đầy đủ
  final String? studentId;  // Mã học sinh (null nếu là giáo viên/admin)
  final String? classId;    // Lớp học
  final UserRole role;      // Phân quyền
  final String? avatarUrl;  // URL ảnh đại diện trên Firebase Storage
  final bool isActive;      // Tài khoản có đang hoạt động không
  final bool hasFaceRegistered; // Đã đăng ký khuôn mặt chưa

  const UserEntity({
    required this.id,
    required this.email,
    required this.fullName,
    this.studentId,
    this.classId,
    required this.role,
    this.avatarUrl,
    this.isActive = true,
    this.hasFaceRegistered = false,
  });

  /// Tiện ích kiểm tra role
  bool get isStudent => role == UserRole.student;
  bool get isTeacher => role == UserRole.teacher;
  bool get isAdmin   => role == UserRole.admin;

  @override
  List<Object?> get props => [
    id, email, fullName, studentId, classId,
    role, avatarUrl, isActive, hasFaceRegistered,
  ];
}
