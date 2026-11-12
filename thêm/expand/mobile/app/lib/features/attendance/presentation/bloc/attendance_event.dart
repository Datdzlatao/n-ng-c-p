import 'package:equatable/equatable.dart';
import '../../domain/entities/attendance_entity.dart';

abstract class AttendanceEvent extends Equatable {
  const AttendanceEvent();
  @override
  List<Object?> get props => [];
}

class MarkAttendanceRequested extends AttendanceEvent {
  final AttendanceEntity attendance;
  const MarkAttendanceRequested(this.attendance);
  @override
  List<Object> get props => [attendance];
}

class LoadAttendanceHistory extends AttendanceEvent {
  final String studentId;
  final String classId;
  const LoadAttendanceHistory({required this.studentId, required this.classId});
  @override
  List<Object> get props => [studentId, classId];
}

class SyncOfflineRequested extends AttendanceEvent {}
