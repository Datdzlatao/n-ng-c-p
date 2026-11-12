import 'package:equatable/equatable.dart';
import '../../domain/entities/attendance_entity.dart';

abstract class AttendanceState extends Equatable {
  const AttendanceState();
  @override
  List<Object?> get props => [];
}

class AttendanceInitial extends AttendanceState {}
class AttendanceLoading extends AttendanceState {}

class AttendanceMarked extends AttendanceState {
  final AttendanceEntity attendance;
  const AttendanceMarked(this.attendance);
  @override
  List<Object> get props => [attendance];
}

class AttendanceHistoryLoaded extends AttendanceState {
  final List<AttendanceEntity> attendances;
  const AttendanceHistoryLoaded(this.attendances);
  @override
  List<Object> get props => [attendances];
}

class AttendanceError extends AttendanceState {
  final String message;
  const AttendanceError(this.message);
  @override
  List<Object> get props => [message];
}

class AttendanceSynced extends AttendanceState {}
