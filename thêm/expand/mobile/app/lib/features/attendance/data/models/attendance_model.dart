import '../../domain/entities/attendance_entity.dart';

class AttendanceModel extends AttendanceEntity {
  const AttendanceModel({
    required super.id,
    required super.studentId,
    required super.studentName,
    required super.sessionId,
    required super.classId,
    required super.timestamp,
    required super.method,
    required super.status,
    super.dressCodePassed,
    super.isSynced,
  });

  factory AttendanceModel.fromJson(Map<String, dynamic> json) {
    return AttendanceModel(
      id:            json['id'] as String,
      studentId:     json['studentId'] as String,
      studentName:   json['studentName'] as String,
      sessionId:     json['sessionId'] as String,
      classId:       json['classId'] as String,
      timestamp:     DateTime.parse(json['timestamp'] as String),
      method:        json['method'] == 'qrCode'
                         ? AttendanceMethod.qrCode
                         : AttendanceMethod.faceId,
      status:        _parseStatus(json['status'] as String? ?? 'present'),
      dressCodePassed: json['dressCodePassed'] as bool? ?? true,
      isSynced:      json['isSynced'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() => {
    'id':            id,
    'studentId':     studentId,
    'studentName':   studentName,
    'sessionId':     sessionId,
    'classId':       classId,
    'timestamp':     timestamp.toIso8601String(),
    'method':        method == AttendanceMethod.qrCode ? 'qrCode' : 'faceId',
    'status':        status.name,
    'dressCodePassed': dressCodePassed,
    'isSynced':      isSynced,
  };

  static AttendanceStatus _parseStatus(String s) {
    switch (s) {
      case 'late':   return AttendanceStatus.late;
      case 'absent': return AttendanceStatus.absent;
      default:       return AttendanceStatus.present;
    }
  }
}
