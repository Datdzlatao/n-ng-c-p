import 'package:equatable/equatable.dart';
import '../../../auth/domain/entities/user_entity.dart';

abstract class QrEvent extends Equatable {
  const QrEvent();
  @override
  List<Object?> get props => [];
}

/// Tạo QR mới cho session
class GenerateQrRequested extends QrEvent {
  final String sessionId;
  final UserEntity teacher;
  final String classId;
  const GenerateQrRequested({
    required this.sessionId,
    required this.teacher,
    required this.classId,
  });
  @override
  List<Object> get props => [sessionId, teacher, classId];
}

/// Làm mới QR (tái tạo sau khi hết hạn)
class QrRefreshRequested extends QrEvent {
  final String sessionId;
  final UserEntity teacher;
  final String classId;
  const QrRefreshRequested({
    required this.sessionId,
    required this.teacher,
    required this.classId,
  });
  @override
  List<Object> get props => [sessionId, teacher, classId];
}

/// Scan QR từ camera
class QrScanned extends QrEvent {
  final String rawData;
  const QrScanned(this.rawData);
  @override
  List<Object> get props => [rawData];
}

/// Reset về trạng thái ban đầu
class QrReset extends QrEvent {}
