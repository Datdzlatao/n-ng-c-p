import 'dart:async';
import 'package:dio/dio.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/security/secure_storage_service.dart';
import '../../domain/entities/attendance_entity.dart';
import '../../domain/entities/attendance_session_entity.dart';
import '../models/attendance_model.dart';
import 'attendance_remote_datasource.dart';

/// Hiện thực AttendanceRemoteDataSource kết nối trực tiếp với FastAPI REST API Backend
class AttendanceRemoteDataSourceRestImpl implements AttendanceRemoteDataSource {
  final Dio dio;
  final SecureStorageService storage;

  AttendanceRemoteDataSourceRestImpl({
    required this.dio,
    required this.storage,
  });

  Future<String> _getBaseUrl() async {
    final customUrl = await storage.read(AppConstants.keyApiBaseUrl);
    return (customUrl != null && customUrl.isNotEmpty)
        ? customUrl.replaceAll(RegExp(r'/+$'), '')
        : AppConstants.defaultApiBaseUrl;
  }

  Future<int> _getSchoolId() async {
    final sIdStr = await storage.read(AppConstants.keySchoolId);
    return int.tryParse(sIdStr ?? '1') ?? 1;
  }

  Future<Options> _authOptions() async {
    final token = await storage.read(AppConstants.keyAuthToken);
    return Options(
      headers: {
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
  }

  @override
  Future<void> saveAttendance(AttendanceModel attendance) async {
    try {
      final baseUrl = await _getBaseUrl();
      final schoolId = await _getSchoolId();
      final options = await _authOptions();

      await dio.post(
        '$baseUrl/api/v1/s/$schoolId/attendance/sync',
        data: {
          'station_secret_key': 'MOBILE_APP_KEY',
          'student_code': attendance.studentId,
          'timestamp': attendance.timestamp.toIso8601String(),
          'direction': 'IN',
          'check_type': attendance.method == AttendanceMethod.qrCode ? 'QR_SCAN' : 'FACE_AI',
          'status': attendance.status == AttendanceStatus.late ? 'LATE' : 'ON_TIME',
          'uniform_status': attendance.dressCodePassed ? 'OK' : 'VIOLATION',
        },
        options: options,
      );
    } catch (e) {
      throw ServerException('Không thể gửi dữ liệu điểm danh: $e');
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
      final baseUrl = await _getBaseUrl();
      final schoolId = await _getSchoolId();
      final options = await _authOptions();

      // Gọi API tra cứu lịch sử điểm danh của học sinh
      final response = await dio.get(
        '$baseUrl/api/v1/s/$schoolId/attendance/student/$studentId',
        options: options,
      );

      if (response.statusCode == 200 && response.data is List) {
        final list = response.data as List;
        return list.map((item) {
          final row = item as Map<String, dynamic>;
          final timestampStr = row['timestamp'] as String? ?? DateTime.now().toIso8601String();
          final rawStatus = (row['status'] as String? ?? 'ON_TIME').toUpperCase();
          final checkType = (row['check_type'] as String? ?? 'FACE_AI').toUpperCase();

          AttendanceStatus status = AttendanceStatus.present;
          if (rawStatus == 'LATE') {
            status = AttendanceStatus.late;
          } else if (rawStatus == 'ABSENT') {
            status = AttendanceStatus.absent;
          }

          return AttendanceModel(
            id: row['id']?.toString() ?? '0',
            studentId: row['student_code']?.toString() ?? studentId,
            studentName: row['full_name']?.toString() ?? 'Học sinh',
            sessionId: 'daily',
            classId: classId,
            timestamp: DateTime.tryParse(timestampStr.replaceAll(' ', 'T')) ?? DateTime.now(),
            method: checkType == 'QR_SCAN' ? AttendanceMethod.qrCode : AttendanceMethod.faceId,
            status: status,
            dressCodePassed: (row['uniform_status'] as String? ?? 'OK').toUpperCase() == 'OK',
            isSynced: true,
          );
        }).toList();
      }
      return [];
    } catch (e) {
      throw ServerException('Lỗi lấy lịch sử điểm danh: $e');
    }
  }

  @override
  Future<String> createSession({
    required String teacherId,
    required String classId,
    required String subject,
  }) async {
    return 'sess_${DateTime.now().millisecondsSinceEpoch}';
  }

  @override
  Future<void> closeSession(String sessionId) async {}

  @override
  Stream<AttendanceSessionEntity?> watchActiveSession(String classId) {
    // Trả về stream giả lập cho session lớp học
    return Stream.value(null);
  }

  @override
  Stream<List<AttendanceModel>> watchSessionAttendances(String sessionId) {
    return Stream.value([]);
  }
}
