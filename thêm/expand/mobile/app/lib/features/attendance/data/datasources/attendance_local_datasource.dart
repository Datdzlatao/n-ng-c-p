// Stub implementation — số lượng mã offline minimal, sẽ expand sau
import '../../domain/entities/attendance_entity.dart';
import '../models/attendance_model.dart';

abstract class AttendanceLocalDataSource {
  Future<void> saveOffline(AttendanceModel attendance);
  Future<List<AttendanceModel>> getUnsyncedAttendances();
  Future<void> markSynced(String attendanceId);
  Future<void> clearSynced();
}

class AttendanceLocalDataSourceImpl implements AttendanceLocalDataSource {
  // Bộ nhớ tạm — Phase 5 sẽ thay bằng Drift SQLite
  final List<AttendanceModel> _buffer = [];

  @override
  Future<void> saveOffline(AttendanceModel attendance) async {
    _buffer.add(attendance);
  }

  @override
  Future<List<AttendanceModel>> getUnsyncedAttendances() async {
    return _buffer.where((a) => !a.isSynced).toList();
  }

  @override
  Future<void> markSynced(String attendanceId) async {
    final idx = _buffer.indexWhere((a) => a.id == attendanceId);
    if (idx >= 0) {
      _buffer[idx] = AttendanceModel(
        id: _buffer[idx].id,
        studentId: _buffer[idx].studentId,
        studentName: _buffer[idx].studentName,
        sessionId: _buffer[idx].sessionId,
        classId: _buffer[idx].classId,
        timestamp: _buffer[idx].timestamp,
        method: _buffer[idx].method,
        status: _buffer[idx].status,
        dressCodePassed: _buffer[idx].dressCodePassed,
        isSynced: true,
      );
    }
  }

  @override
  Future<void> clearSynced() async {
    _buffer.removeWhere((a) => a.isSynced);
  }
}
