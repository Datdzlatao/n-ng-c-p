import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/attendance_entity.dart';
import '../entities/attendance_session_entity.dart';

abstract class AttendanceRepository {
  Future<Either<Failure, void>> markAttendance(AttendanceEntity attendance);
  Future<Either<Failure, List<AttendanceEntity>>> getHistory({
    required String studentId,
    required String classId,
    DateTime? fromDate,
    DateTime? toDate,
  });
  Future<Either<Failure, void>> syncOffline();
  Future<Either<Failure, AttendanceSessionEntity>> createSession({
    required String teacherId,
    required String classId,
    required String subject,
  });
  Future<Either<Failure, void>> closeSession(String sessionId);
  Stream<AttendanceSessionEntity?> watchActiveSession(String classId);
  Stream<List<AttendanceEntity>> watchSessionAttendances(String sessionId);
}
