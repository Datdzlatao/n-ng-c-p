import 'package:equatable/equatable.dart';

class AttendanceSessionEntity extends Equatable {
  final String id;
  final String teacherId;
  final String classId;
  final String subject;       // Môn học
  final DateTime startTime;
  final DateTime? endTime;
  final bool isActive;
  final int presentCount;     // Số học sinh đã điểm danh
  final int totalStudents;    // Tổng số học sinh trong lớp

  const AttendanceSessionEntity({
    required this.id,
    required this.teacherId,
    required this.classId,
    required this.subject,
    required this.startTime,
    this.endTime,
    this.isActive = true,
    this.presentCount = 0,
    this.totalStudents = 0,
  });

  double get attendanceRate =>
      totalStudents > 0 ? presentCount / totalStudents : 0.0;

  @override
  List<Object?> get props => [
    id, teacherId, classId, subject, startTime,
    endTime, isActive, presentCount, totalStudents,
  ];
}
