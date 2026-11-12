import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/attendance_entity.dart';
import '../repositories/attendance_repository.dart';

class GetAttendanceHistoryUseCase {
  final AttendanceRepository repository;
  const GetAttendanceHistoryUseCase(this.repository);

  Future<Either<Failure, List<AttendanceEntity>>> call({
    required String studentId,
    required String classId,
    DateTime? fromDate,
    DateTime? toDate,
  }) {
    return repository.getHistory(
      studentId: studentId,
      classId: classId,
      fromDate: fromDate,
      toDate: toDate,
    );
  }
}
