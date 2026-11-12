import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../repositories/attendance_repository.dart';

class SyncOfflineAttendanceUseCase {
  final AttendanceRepository repository;
  const SyncOfflineAttendanceUseCase(this.repository);

  Future<Either<Failure, void>> call() => repository.syncOffline();
}
