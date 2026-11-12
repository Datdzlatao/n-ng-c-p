import 'package:dartz/dartz.dart';
import 'package:uuid/uuid.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../../../core/network/network_info.dart';
import '../../domain/entities/attendance_entity.dart';
import '../../domain/entities/attendance_session_entity.dart';
import '../../domain/repositories/attendance_repository.dart';
import '../datasources/attendance_remote_datasource.dart';
import '../datasources/attendance_local_datasource.dart';
import '../models/attendance_model.dart';

class AttendanceRepositoryImpl implements AttendanceRepository {
  final AttendanceRemoteDataSource remoteDataSource;
  final AttendanceLocalDataSource localDataSource;
  final NetworkInfo networkInfo;
  final _uuid = const Uuid();

  const AttendanceRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
    required this.networkInfo,
  });

  @override
  Future<Either<Failure, void>> markAttendance(AttendanceEntity attendance) async {
    final model = _toModel(attendance);
    if (await networkInfo.isConnected) {
      try {
        await remoteDataSource.saveAttendance(model);
        return const Right(null);
      } catch (e) {
        // Fallback sang offline nếu lưu server thất bại
        await localDataSource.saveOffline(model);
        return const Right(null);
      }
    } else {
      // Không có mạng — lưu vào local buffer
      await localDataSource.saveOffline(model);
      return const Right(null);
    }
  }

  @override
  Future<Either<Failure, List<AttendanceEntity>>> getHistory({
    required String studentId,
    required String classId,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    try {
      final list = await remoteDataSource.getHistory(
        studentId: studentId,
        classId: classId,
        from: fromDate,
        to: toDate,
      );
      return Right(list);
    } on ServerException catch (e) {
      return Left(ServerFailure(e.message));
    }
  }

  @override
  Future<Either<Failure, void>> syncOffline() async {
    if (!await networkInfo.isConnected) return const Right(null);
    try {
      final unsynced = await localDataSource.getUnsyncedAttendances();
      for (final a in unsynced) {
        await remoteDataSource.saveAttendance(a);
        await localDataSource.markSynced(a.id);
      }
      await localDataSource.clearSynced();
      return const Right(null);
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, AttendanceSessionEntity>> createSession({
    required String teacherId,
    required String classId,
    required String subject,
  }) async {
    try {
      final sessionId = await remoteDataSource.createSession(
        teacherId: teacherId,
        classId: classId,
        subject: subject,
      );
      return Right(AttendanceSessionEntity(
        id: sessionId,
        teacherId: teacherId,
        classId: classId,
        subject: subject,
        startTime: DateTime.now(),
      ));
    } on ServerException catch (e) {
      return Left(ServerFailure(e.message));
    }
  }

  @override
  Future<Either<Failure, void>> closeSession(String sessionId) async {
    try {
      await remoteDataSource.closeSession(sessionId);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(ServerFailure(e.message));
    }
  }

  @override
  Stream<AttendanceSessionEntity?> watchActiveSession(String classId) =>
      remoteDataSource.watchActiveSession(classId);

  @override
  Stream<List<AttendanceEntity>> watchSessionAttendances(String sessionId) =>
      remoteDataSource.watchSessionAttendances(sessionId);

  AttendanceModel _toModel(AttendanceEntity e) => AttendanceModel(
    id: e.id.isEmpty ? _uuid.v4() : e.id,
    studentId: e.studentId,
    studentName: e.studentName,
    sessionId: e.sessionId,
    classId: e.classId,
    timestamp: e.timestamp,
    method: e.method,
    status: e.status,
    dressCodePassed: e.dressCodePassed,
    isSynced: false,
  );
}
