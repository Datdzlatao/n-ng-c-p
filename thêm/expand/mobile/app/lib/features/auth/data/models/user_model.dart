import '../../domain/entities/user_entity.dart';

/// Data model — biết cách parse từ/sang Firestore JSON
class UserModel extends UserEntity {
  const UserModel({
    required super.id,
    required super.email,
    required super.fullName,
    super.studentId,
    super.classId,
    required super.role,
    super.avatarUrl,
    super.isActive,
    super.hasFaceRegistered,
  });

  /// Parse từ Firestore document data
  factory UserModel.fromJson(Map<String, dynamic> json, String uid) {
    return UserModel(
      id:        uid,
      email:     json['email'] as String? ?? '',
      fullName:  json['fullName'] as String? ?? '',
      studentId: json['studentId'] as String?,
      classId:   json['classId'] as String?,
      role: _parseRole(json['role'] as String? ?? 'student'),
      avatarUrl: json['avatarUrl'] as String?,
      isActive:  json['isActive'] as bool? ?? true,
      hasFaceRegistered: json['hasFaceRegistered'] as bool? ?? false,
    );
  }

  /// Chuyển sang Map để lưu lên Firestore
  Map<String, dynamic> toJson() => {
    'email':     email,
    'fullName':  fullName,
    'studentId': studentId,
    'classId':   classId,
    'role':      role.name, // 'student', 'teacher', 'admin'
    'avatarUrl': avatarUrl,
    'isActive':  isActive,
    'hasFaceRegistered': hasFaceRegistered,
    'updatedAt': DateTime.now().toIso8601String(),
  };

  static UserRole _parseRole(String value) {
    switch (value) {
      case 'teacher': return UserRole.teacher;
      case 'admin':   return UserRole.admin;
      default:        return UserRole.student;
    }
  }

  /// Tạo bản copy với một số field thay đổi
  UserModel copyWith({
    String? fullName,
    String? avatarUrl,
    bool? isActive,
    bool? hasFaceRegistered,
  }) {
    return UserModel(
      id: id, email: email, role: role,
      studentId: studentId, classId: classId,
      fullName:          fullName          ?? this.fullName,
      avatarUrl:         avatarUrl         ?? this.avatarUrl,
      isActive:          isActive          ?? this.isActive,
      hasFaceRegistered: hasFaceRegistered ?? this.hasFaceRegistered,
    );
  }
}
