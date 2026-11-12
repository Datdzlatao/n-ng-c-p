import 'dart:convert';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/security/encryption_service.dart';
import '../../../../core/utils/date_utils.dart';
import '../../domain/entities/qr_payload_entity.dart';

/// Dịch vụ tạo và xác minh QR Code
class QrService {
  final EncryptionService encryptionService;

  const QrService({required this.encryptionService});

  /// Tạo QR string đã mã hóa từ session data
  /// Flow: JSON payload -> HMAC sign -> AES-256 encrypt -> base64url string
  String generateQrString({
    required String sessionId,
    required String teacherId,
    required String classId,
  }) {
    final now   = DateTime.now();
    final nonce = encryptionService.generateNonce();

    // Xây dựng payload JSON
    final payloadMap = {
      'sessionId': sessionId,
      'teacherId': teacherId,
      'classId':   classId,
      'ts':        now.millisecondsSinceEpoch,
      'nonce':     nonce,
    };
    final payloadJson = jsonEncode(payloadMap);

    // Ký HMAC-SHA256
    final signature = encryptionService.sign(payloadJson);
    payloadMap['sig'] = signature;

    // Mã hóa toàn bộ payload (bao gồm cả signature)
    return encryptionService.encrypt(jsonEncode(payloadMap));
  }

  /// Xác minh và giải mã QR string
  /// Throw QrException nếu QR không hợp lệ hoặc đã hết hạn
  QrPayloadEntity validateQrString(String qrString) {
    try {
      // Giải mã AES
      final decrypted = encryptionService.decrypt(qrString);
      final map = jsonDecode(decrypted) as Map<String, dynamic>;

      // Lấy signature ra rồi verify
      final signature = map.remove('sig') as String? ?? '';
      final dataJson  = jsonEncode(map);
      if (!encryptionService.verify(dataJson, signature)) {
        throw const QrException('Chữ ký QR không hợp lệ');
      }

      // Kiểm tra TTL
      final ts = map['ts'] as int;
      final createdAt = DateTime.fromMillisecondsSinceEpoch(ts);
      if (!AppDateUtils.isWithinTtl(createdAt, AppConstants.qrTtlSeconds)) {
        throw const QrException('Mã QR đã hết hạn. Vui lòng quét mã mới');
      }

      return QrPayloadEntity(
        sessionId: map['sessionId'] as String,
        teacherId: map['teacherId'] as String,
        classId:   map['classId'] as String,
        createdAt: createdAt,
        nonce:     map['nonce'] as String,
        signature: signature,
      );
    } on QrException {
      rethrow;
    } catch (e) {
      throw const QrException('Mã QR không đọc được');
    }
  }
}
