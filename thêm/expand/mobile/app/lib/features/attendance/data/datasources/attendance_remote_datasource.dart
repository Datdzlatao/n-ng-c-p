import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:uuid/uuid.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/errors/exceptions.dart';
import '../../domain/entities/attendance_entity.dart';
import '../../domain/entities/attendance_session_entity.dart';
import '../models/attendance_model.dart';

abstract class AttendanceRemoteDataSource {
  Future<void> saveAttendance(AttendanceModel attendance);
  Future<List<AttendanceModel>> getHistory({required String studentId, required String classId, DateTime? from, DateTime? to});
  Future<String> createSession({required String teacherId, required String classId, required String subject});
  Future<void> closeSession(String sessionId);
  Stream<AttendanceSessionEntity?> watchActiveSession(String classId);
  Stream<List<AttendanceModel>> watchSessionAttendances(String sessionId);
}

class AttendanceRemoteDataSourceImpl implements AttendanceRemoteDataSource {
  final FirebaseFirestore firestore;
  final _uuid = const Uuid();

  const AttendanceRemoteDataSourceImpl({required this.firestore});

  @override
  Future<void> saveAttendance(AttendanceModel attendance) async {
    try {
      await firestore
          .collection(AppConstants.colAttendances)
          .doc(attendance.id)
          .set(attendance.toJson());
    } catch (e) {
      throw ServerException(e.toString());
    }
  }

  @override
  Future<List<AttendanceModel>> getHistory({
    required String studentId,
    required String classId,
    DateTime? from,
    DateTime? to,
  }) async {
    try {
      var query = firestore
          .collection(AppConstants.colAttendances)
          .where('studentId', isEqualTo: studentId)
          .where('classId', isEqualTo: classId)
          .orderBy('timestamp', descending: true);

      if (from != null) query = query.where('timestamp', isGreaterThanOrEqualTo: from.toIso8601String());
      if (to   != null) query = query.where('timestamp', isLessThanOrEqualTo: to.toIso8601String());

      final snap = await query.limit(50).get();
      return snap.docs.map((d) => AttendanceModel.fromJson(d.data())).toList();
    } catch (e) {
      throw ServerException(e.toString());
    }
  }

  @override
  Future<String> createSession({
    required String teacherId,
    required String classId,
    required String subject,
  }) async {
    final id  = _uuid.v4();
    final now = DateTime.now();
    await firestore.collection(AppConstants.colSessions).doc(id).set({
      'id':        id,
      'teacherId': teacherId,
      'classId':   classId,
      'subject':   subject,
      'startTime': now.toIso8601String(),
      'isActive':  true,
      'presentCount': 0,
    });
    return id;
  }

  @override
  Future<void> closeSession(String sessionId) async {
    await firestore.collection(AppConstants.colSessions).doc(sessionId).update({
      'isActive': false,
      'endTime':  DateTime.now().toIso8601String(),
    });
  }

  @override
  Stream<AttendanceSessionEntity?> watchActiveSession(String classId) {
    return firestore
        .collection(AppConstants.colSessions)
        .where('classId', isEqualTo: classId)
        .where('isActive', isEqualTo: true)
        .limit(1)
        .snapshots()
        .map((snap) {
      if (snap.docs.isEmpty) return null;
      final d = snap.docs.first.data();
      return AttendanceSessionEntity(
        id:          d['id'] as String,
        teacherId:   d['teacherId'] as String,
        classId:     d['classId'] as String,
        subject:     d['subject'] as String,
        startTime:   DateTime.parse(d['startTime'] as String),
        isActive:    d['isActive'] as bool,
        presentCount: d['presentCount'] as int? ?? 0,
      );
    });
  }

  @override
  Stream<List<AttendanceModel>> watchSessionAttendances(String sessionId) {
    return firestore
        .collection(AppConstants.colAttendances)
        .where('sessionId', isEqualTo: sessionId)
        .orderBy('timestamp', descending: false)
        .snapshots()
        .map((snap) =>
            snap.docs.map((d) => AttendanceModel.fromJson(d.data())).toList());
  }
}
