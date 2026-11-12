import 'package:equatable/equatable.dart';
import '../../domain/entities/qr_payload_entity.dart';

abstract class QrState extends Equatable {
  const QrState();
  @override
  List<Object?> get props => [];
}

class QrInitial extends QrState {}
class QrLoading extends QrState {}

/// Tạo QR thành công — hiển thị mã QR cho student quét
class QrGenerated extends QrState {
  final String qrString;    // Chuỗi đã mã hóa đưa vào QR widget
  final DateTime expiresAt; // Thông báo thời gian hết hạn
  const QrGenerated({required this.qrString, required this.expiresAt});
  @override
  List<Object> get props => [qrString, expiresAt];
}

/// Scan QR thành công — payload đã decode
class QrScanSuccess extends QrState {
  final QrPayloadEntity payload;
  const QrScanSuccess(this.payload);
  @override
  List<Object> get props => [payload];
}

/// Lỗi (QR hết hạn, chữ ký sai, v.v.)
class QrError extends QrState {
  final String message;
  const QrError(this.message);
  @override
  List<Object> get props => [message];
}

/// QR đã hết hạn TTL — cần refresh
class QrExpired extends QrState {}
