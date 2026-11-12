import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/attendance_entity.dart';
import '../repositories/attendance_repository.dart';

class MarkAttendanceUseCase {
  final AttendanceRepository repository;
  const MarkAttendanceUseCase(this.repository);

  Future<Either<Failure, void>> call(AttendanceEntity attendance) {
    return repository.markAttendance(attendance);
  }
}
